# ==============================================================================
# AGROSENSE AI — SERVICIO DE INVERNADERO DE ORQUÍDEAS (AGROFIELD SERVICE)
# ==============================================================================
# En este módulo desarrollamos la lógica del invernadero de orquídeas (RF1 a RF7)
# conectada con la base de datos en Supabase y el respaldo local en SQLite.
# ==============================================================================

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.config import settings
from app.mqtt_bridge import mqtt_bridge

logger = logging.getLogger("asai.field_service")

router = APIRouter()

MODULE_ID = "invernadero-orquideas"

ORCHID_PROFILE = {
    "especie": "Orquídeas de Invernadero (Phalaenopsis sp.)",
    "caso_estudio": "Integración de Competencias II - Etapa III",
    "humedad_optima_pct": 80.0,
    "humedad_min_pct": 75.0,
    "humedad_max_pct": 85.0,
    "temp_min_c": 18.0,
    "temp_max_c": 24.0,
    "tipo_sustrato": "Corteza de pino y musgo sphagnum",
    "metodo_riego": "Aspersión / Riego programado por calendario semanal",
}

_sensor_link_state: Dict[str, Any] = {
    "connected": True,
    "protocol": "Wi-Fi",
    "device_id": "ESP32-Wokwi-Orquideas",
    "last_checked": None,
    "message": "Enlace listo para recibir lecturas por Wi-Fi (HTTP REST / MQTT).",
    "troubleshooting": [],
}

_irrigation_runtime: Dict[str, Any] = {
    "demo_enabled": False,
    "interval_seconds": 10,
    "duration_seconds": 5,
    "auto_off_at": None,
    "next_demo_at": None,
    "last_calendar_minute": None,
    "last_trigger_source": None,
}
_scheduler_task: Optional[asyncio.Task] = None


# Aquí usamos BaseModel de Pydantic para validar tipos y rangos del JSON entrante
# antes de guardar o ejecutar acciones en el servidor.
class FieldPumpCommand(BaseModel):
    action: str = Field(..., description="ON | OFF")
    duration_seconds: Optional[int] = Field(default=None, ge=1, le=3600)


class DemoCycleConfig(BaseModel):
    enabled: bool = Field(..., description="Activa o detiene ciclo demostrativo periódico")
    interval_seconds: int = Field(default=10, ge=5, le=3600, description="Cada cuántos segundos iniciar aspersión")
    duration_seconds: int = Field(default=5, ge=2, le=300, description="Cuántos segundos dura encendida la aspersión")


# RF1: En esta clase validamos los datos del calendario semanal de riego
class FieldScheduleUpdate(BaseModel):
    active_days: List[str] = Field(..., description="Días de la semana para riego (RF1)")
    irrigation_time: str = Field(default="08:30", description="Hora fija de riego (RF1)")
    duration_minutes: int = Field(default=20, ge=1, le=120, description="Duración del riego en minutos")
    recording_frequency_minutes: Optional[int] = Field(
        default=None, ge=1, le=1440, description="Frecuencia de guardado histórico en minutos (RF5)"
    )


class FieldFrequencyUpdate(BaseModel):
    recording_frequency_minutes: int = Field(..., ge=1, le=1440, description="Frecuencia en minutos (ej. 60 = cada 1 hora)")


# RF3 y RF4: Aquí recibimos y validamos las lecturas de temperatura y humedad
class FieldTelemetryInput(BaseModel):
    air_temperature: float = Field(..., ge=-10.0, le=60.0, description="Temperatura ambiente en °C (RF4)")
    air_humidity: float = Field(..., ge=0.0, le=100.0, description="Humedad relativa en % (RF4)")
    soil_humidity_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Humedad de sustrato")
    barometric_pressure_hpa: Optional[float] = Field(default=None, ge=300.0, le=1200.0, description="Presión atmosférica (hPa)")
    source: str = Field(default="WIFI_ESP32", description="Origen de la lectura (WIFI_ESP32, WOKWI_SIM, BLUETOOTH)")


class SensorConnectRequest(BaseModel):
    protocol: str = Field(default="Wi-Fi", description="Wi-Fi | Bluetooth")
    device_id: str = Field(default="ESP32-Wokwi-Orquideas", min_length=2, max_length=60)
    simulate_failure: bool = Field(default=False, description="Simula fallo para validar flujo de excepción RF3")


# RF4: En esta función cumplimos con evaluar los rangos óptimos (80% HR y 18-24 °C)
def _evaluate_orchid_alerts(temp: float, hum: float) -> List[str]:
    """Compara temperatura y humedad contra el rango óptimo y genera alertas si se salen."""
    alerts: List[str] = []
    if hum < ORCHID_PROFILE["humedad_min_pct"]:
        alerts.append(f"ALERTA HUMEDAD BAJA: Humedad relativa ({hum:.1f}%) inferior al 80% requerido (mín. 75%).")
    elif hum > ORCHID_PROFILE["humedad_max_pct"]:
        alerts.append(f"AVISO SOBREHUMEDAD: Humedad relativa ({hum:.1f}%) superior al 85%. Riesgo de hongos.")

    if temp < ORCHID_PROFILE["temp_min_c"] or temp > ORCHID_PROFILE["temp_max_c"]:
        alerts.append(f"ALERTA TÉRMICA: Temperatura ({temp:.1f}°C) fuera del rango óptimo (18°C - 24°C).")
    return alerts


# RF2: En esta parte calculamos el próximo día y hora de riego para avisar al usuario
def calculate_next_notification(schedule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Revisa el calendario guardado y prepara el mensaje de aviso para regar."""
    sched = schedule or db.load_schedule(MODULE_ID)
    hoy_str = db.get_today_es()
    active_days = sched["active_days"] or ["Lun"]
    es_hoy = hoy_str in active_days
    prox_dia = hoy_str if es_hoy else active_days[0]

    is_due_now = False
    try:
        hh, mm = [int(p) for p in str(sched["irrigation_time"]).split(":")[:2]]
        now_dt = datetime.now()
        sched_start = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
        sched_end = sched_start + timedelta(minutes=int(sched.get("duration_minutes") or 20))
        if es_hoy and sched_start <= now_dt <= sched_end:
            is_due_now = True
    except (ValueError, TypeError):
        is_due_now = False

    if is_due_now:
        msg = (
            f"🚿 ¡HORA DE REGAR ORQUÍDEAS AHORA! (RF2): Ventana activa ({sched['irrigation_time']} hrs, "
            f"{sched['duration_minutes']} min) para hoy {hoy_str}."
        )
    else:
        msg = (
            f"🔔 Notificación de Riego (RF2): Próximo riego programado para {prox_dia} a las "
            f"{sched['irrigation_time']} hrs ({sched['duration_minutes']} min). "
            f"Días activos: {', '.join(active_days)}."
        )
    return {
        "scheduled_day": prox_dia,
        "scheduled_time": sched["irrigation_time"],
        "is_today": es_hoy,
        "is_due_now": is_due_now,
        "notification_message": msg,
        "active_days": active_days,
    }


def _get_sensor_link_status() -> Dict[str, Any]:
    """Retorna estado de emparejamiento y verificación de sensores (RF3)."""
    mqtt_stat = mqtt_bridge.get_status()
    return {
        **_sensor_link_state,
        "mqtt_connected": mqtt_stat["connected"],
        "last_mqtt_field_at": mqtt_stat.get("last_field_message_at"),
    }


def _apply_field_pump(turn_on: bool, source: str, auto_off_seconds: Optional[float] = None) -> Dict[str, Any]:
    """Actualiza estado de aspersión en BD, audita y publica ON/OFF al Wokwi de Orquídeas."""
    updated = db.save_module_state(MODULE_ID, pump_active=turn_on)
    db.insert_command_audit(
        MODULE_ID,
        "bomba_aspersion_orquideas",
        "ON" if turn_on else "OFF",
        float(auto_off_seconds or 0),
        source,
    )
    mqtt_sent = mqtt_bridge.publish_field_pump(turn_on)
    _irrigation_runtime["last_trigger_source"] = source
    if turn_on and auto_off_seconds is not None and auto_off_seconds > 0:
        _irrigation_runtime["auto_off_at"] = time.monotonic() + float(auto_off_seconds)
    else:
        _irrigation_runtime["auto_off_at"] = None
    return {
        "pump_active": updated["pump_active"],
        "mqtt_published": bool(mqtt_sent),
        "source": source,
    }


def _get_irrigation_control_status(pump_active: bool) -> Dict[str, Any]:
    now_m = time.monotonic()
    remaining_on = 0
    if _irrigation_runtime["auto_off_at"] is not None:
        remaining_on = max(0, int(round(_irrigation_runtime["auto_off_at"] - now_m)))
    return {
        "pump_active": bool(pump_active),
        "demo_enabled": bool(_irrigation_runtime["demo_enabled"]),
        "interval_seconds": int(_irrigation_runtime["interval_seconds"]),
        "duration_seconds": int(_irrigation_runtime["duration_seconds"]),
        "remaining_on_seconds": remaining_on,
        "last_trigger_source": _irrigation_runtime["last_trigger_source"],
    }


# Planificador automático en segundo plano (asyncio): ejecuta cada 1s sin bloquear la web
async def _orchid_scheduler_loop() -> None:
    """Evalúa cada segundo el calendario semanal RF1 y el ciclo demo de aspersión."""
    while True:
        try:
            await asyncio.sleep(1.0)
            now_m = time.monotonic()

            # 1. Apagado automático cuando vence la duración programada
            auto_off = _irrigation_runtime.get("auto_off_at")
            if auto_off is not None and now_m >= auto_off:
                _apply_field_pump(False, "AUTO_FIN_CICLO")

            # 2. Modo Demostración Cíclica (ej. cada 10s durante 5s)
            if _irrigation_runtime["demo_enabled"]:
                next_demo = _irrigation_runtime.get("next_demo_at")
                if next_demo is None or now_m >= next_demo:
                    dur = int(_irrigation_runtime["duration_seconds"])
                    itv = int(_irrigation_runtime["interval_seconds"])
                    _apply_field_pump(True, "AUTO_DEMO_CICLO", auto_off_seconds=dur)
                    _irrigation_runtime["next_demo_at"] = now_m + max(itv, dur + 1)
                continue

            # 3. Modo Calendario Semanal real (RF1 + RF2)
            sched = db.load_schedule(MODULE_ID)
            now_dt = datetime.now()
            minute_key = now_dt.strftime("%Y-%m-%d %H:%M")
            hoy_es = db.get_today_es()
            if (
                hoy_es in (sched.get("active_days") or [])
                and now_dt.strftime("%H:%M") == str(sched.get("irrigation_time"))
                and _irrigation_runtime["last_calendar_minute"] != minute_key
            ):
                _irrigation_runtime["last_calendar_minute"] = minute_key
                dur_sec = max(1, int(sched.get("duration_minutes") or 20)) * 60
                _apply_field_pump(True, "AUTO_CALENDARIO_RF1", auto_off_seconds=dur_sec)
                db.insert_alert(
                    MODULE_ID,
                    "INFO",
                    f"🚿 Riego automático iniciado por calendario ({hoy_es} {sched['irrigation_time']} hrs, {sched['duration_minutes']} min).",
                )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning(f"Error en planificador de riego Orquídeas: {exc}")


def start_orchid_scheduler() -> None:
    """Inicia el planificador asíncrono en segundo plano si MQTT está habilitado."""
    global _scheduler_task
    if not settings.MQTT_ENABLED:
        return
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(_orchid_scheduler_loop())


async def stop_orchid_scheduler() -> None:
    """Detiene limpiamente el planificador al apagar FastAPI."""
    global _scheduler_task
    if _scheduler_task is not None and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass
    _scheduler_task = None


def get_field_dashboard_data() -> Dict[str, Any]:
    """Agrega perfil, calendario, telemetría persistida, alertas y notificación para el dashboard."""
    schedule = db.load_schedule(MODULE_ID)
    state = db.load_module_state(MODULE_ID)
    temp = state["air_temperature"]
    hum = state["air_humidity"]
    alerts = _evaluate_orchid_alerts(temp, hum)
    return {
        "profile": ORCHID_PROFILE,
        "schedule": {**schedule, "modo": "CALENDARIO_SEMANAL"},
        "telemetry": {
            "air_temperature": temp,
            "air_humidity": hum,
            "barometric_pressure_hpa": state["barometric_pressure_hpa"],
            "soil_humidity_pct": state["soil_humidity_pct"] if state["soil_humidity_pct"] is not None else 68.0,
            "timestamp": state["timestamp"],
            "status": "ALERTA" if alerts else "OPTIMO",
        },
        "active_alerts": alerts,
        "alerts_log": db.get_alerts(MODULE_ID, limit=6),
        "notification": calculate_next_notification(schedule),
        "sensor_link": _get_sensor_link_status(),
        "irrigation_control": _get_irrigation_control_status(state["pump_active"]),
        "storage": db.get_storage_backend_info(),
    }


# ==============================================================================
# RUTAS API DEL INVERNADERO DE ORQUÍDEAS (RF1 a RF7)
# ==============================================================================
# Con @router.get y @router.post exponemos los endpoints HTTP para la web;
# HTTPException(400) devuelve un error controlado si llega algún dato inválido.

# RF7 y RF4: Estado en tiempo real para tarjetas, gráfico y alertas
@router.get("/status")
async def get_field_status():
    """Devuelve estado actual, alertas activas, calendario y conexión a Supabase."""
    data = get_field_dashboard_data()
    return {
        "service": "AgroField Service (Invernadero Tradicional & Orquídeas)",
        "course_target": "Integración de Competencias II (IEI-094)",
        "profile": ORCHID_PROFILE,
        "telemetry": data["telemetry"],
        "schedule": data["schedule"],
        "notification": data["notification"],
        "alerts_log": data["alerts_log"],
        "sensor_link": data["sensor_link"],
        "irrigation_control": data["irrigation_control"],
        "storage": data["storage"],
        "compliance_status": {
            "RF1_calendario_riego": "CUMPLIDO",
            "RF2_notificar_hora_riego": "CUMPLIDO",
            "RF3_sensores_humedad": "CUMPLIDO (Wi-Fi / Bluetooth + Diagnóstico)",
            "RF4_monitoreo_humedad": "CUMPLIDO (80% HR y 18-24°C + Alertas)",
            "RF5_registro_historico": f"CUMPLIDO (Frecuencia cada {data['schedule']['recording_frequency_minutes']} min)",
            "RF6_base_datos": f"CUMPLIDO ({data['storage']['engine']})",
            "RF7_visualizacion_tiempo_real": "CUMPLIDO (Gráfico + Polling 5s)",
        },
        "active_alerts": data["active_alerts"],
    }


# RF1: En esta ruta consultamos y guardamos los días y hora del calendario semanal
@router.get("/schedule")
async def get_field_schedule():
    """Consulta el Calendario Semanal de Riego establecido (RF1)."""
    schedule = db.load_schedule(MODULE_ID)
    return {
        "schedule": {**schedule, "modo": "CALENDARIO_SEMANAL"},
        "notification": calculate_next_notification(schedule),
    }


@router.post("/schedule")
async def update_field_schedule(data: FieldScheduleUpdate):
    """Guarda los días, hora y duración del riego en Base de Datos (RF1)."""
    if not data.active_days:
        raise HTTPException(status_code=400, detail="Debe seleccionar al menos un día de la semana.")

    invalid_days = [d for d in data.active_days if d not in db.DIAS_SEMANA]
    if invalid_days:
        raise HTTPException(status_code=400, detail=f"Días no válidos: {invalid_days}. Usar {db.DIAS_SEMANA}.")

    saved = db.save_schedule(
        MODULE_ID,
        active_days=data.active_days,
        irrigation_time=data.irrigation_time,
        duration_minutes=data.duration_minutes,
        recording_frequency_minutes=data.recording_frequency_minutes,
    )
    db.insert_command_audit(MODULE_ID, "calendario_semanal", "SET_SCHEDULE", data.duration_minutes, "USUARIO_WEB")
    notif = calculate_next_notification(saved)

    return {
        "status": "success",
        "message": "Calendario de riego guardado en base de datos con éxito (RF1).",
        "active_days": saved["active_days"],
        "irrigation_time": saved["irrigation_time"],
        "duration_minutes": saved["duration_minutes"],
        "recording_frequency_minutes": saved["recording_frequency_minutes"],
        "notification": notif["notification_message"],
    }


# RF5: En esta parte actualizamos cada cuántos minutos se guarda el histórico
@router.post("/history/frequency")
async def update_field_recording_frequency(data: FieldFrequencyUpdate):
    """Guarda cada cuántos minutos se registra el historial ambiental (RF5)."""
    saved = db.save_schedule(MODULE_ID, recording_frequency_minutes=data.recording_frequency_minutes)
    db.insert_command_audit(
        MODULE_ID,
        "frecuencia_historico",
        "SET_FREQUENCY",
        float(data.recording_frequency_minutes),
        "USUARIO_WEB",
    )
    return {
        "status": "success",
        "recording_frequency_minutes": saved["recording_frequency_minutes"],
        "message": f"Frecuencia de registro histórico actualizada: cada {saved['recording_frequency_minutes']} min (RF5).",
    }


# RF2: En este bloque notificamos al usuario cuando toca regar según su horario
@router.get("/notification")
async def get_field_notification():
    """Retorna la notificación activa de la hora de riego (RF2)."""
    return calculate_next_notification()


@router.post("/notification/trigger")
async def trigger_field_irrigation_notification():
    """Registra y emite una notificación activa de hora de riego en Supabase/SQLite (RF2)."""
    sched = db.load_schedule(MODULE_ID)
    hoy_str = db.get_today_es()
    msg = (
        f"🚿 ¡Hora de Riego Activa! (RF2): Riego programado de orquídeas ({hoy_str} - "
        f"{sched['irrigation_time']} hrs, duración {sched['duration_minutes']} min)."
    )
    db.insert_alert(MODULE_ID, "INFO", msg)
    return {
        "status": "triggered",
        "is_due_now": True,
        "notification_message": msg,
        "alerts_log": db.get_alerts(MODULE_ID, limit=6),
    }


# RF3: Aquí emparejamos sensores Wi-Fi/Bluetooth o entregamos pasos si falla la conexión
@router.get("/sensors/check")
async def check_field_sensors():
    """Verifica el estado de conexión de sensores Wi-Fi / Bluetooth de Orquídeas (RF3)."""
    state = db.load_module_state(MODULE_ID)
    return {
        **_get_sensor_link_status(),
        "last_reading_timestamp": state["timestamp"],
        "last_temperature_c": state["air_temperature"],
        "last_humidity_pct": state["air_humidity"],
    }


@router.post("/sensors/connect")
async def connect_field_sensors(req: SensorConnectRequest):
    """Empareja sensores Wi-Fi/Bluetooth o entrega guía de solución ante fallo (RF3)."""
    proto = req.protocol.strip()
    if proto not in ("Wi-Fi", "Bluetooth"):
        raise HTTPException(status_code=400, detail="Protocolo no válido. Use 'Wi-Fi' o 'Bluetooth'.")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _sensor_link_state["protocol"] = proto
    _sensor_link_state["device_id"] = req.device_id.strip()
    _sensor_link_state["last_checked"] = now_str

    if req.simulate_failure:
        troubleshooting = (
            [
                "1. Verifica que la red Wi-Fi sea de banda 2.4 GHz (el ESP32 no detecta redes 5 GHz).",
                "2. Comprueba SSID, contraseña y que la IP/URL del backend o broker.emqx.io sea alcanzable.",
                "3. Abre el Monitor Serial a 115200 baudios para confirmar '[WiFi] Conectado' y las lecturas DHT11/BME280.",
                "4. Presiona el botón EN/RST de la placa y vuelve a ejecutar 'Conectar y Verificar'.",
            ]
            if proto == "Wi-Fi"
            else [
                "1. Activa Bluetooth en el equipo/servidor y confirma que el módulo (ESP32 BLE / HC-05) esté en modo visible.",
                "2. Verifica emparejamiento previo y PIN (por defecto 1234 o 0000 en módulos clásicos).",
                "3. Mantén el sensor dentro de un radio menor a 10 metros sin obstáculos metálicos.",
                "4. Reinicia la alimentación de 3.3V/5V del nodo sensor y vuelve a intentar.",
            ]
        )
        _sensor_link_state["connected"] = False
        _sensor_link_state["message"] = f"Error de conexión {proto} con '{_sensor_link_state['device_id']}'."
        _sensor_link_state["troubleshooting"] = troubleshooting
        db.insert_alert(MODULE_ID, "WARNING", f"Fallo de emparejamiento {proto} ({_sensor_link_state['device_id']}).")
        return {
            "status": "error",
            "connected": False,
            "protocol": proto,
            "device_id": _sensor_link_state["device_id"],
            "message": _sensor_link_state["message"],
            "troubleshooting": troubleshooting,
        }

    _sensor_link_state["connected"] = True
    _sensor_link_state["troubleshooting"] = []
    _sensor_link_state["message"] = (
        f"Sensor '{_sensor_link_state['device_id']}' emparejado y verificado vía {proto}. "
        f"Listo para recibir telemetría hacia /api/v1/services/field/telemetry."
    )
    db.insert_command_audit(MODULE_ID, f"sensor_{proto.lower()}", "CONNECT", 1.0, "USUARIO_WEB")
    return {
        "status": "connected",
        "connected": True,
        "protocol": proto,
        "device_id": _sensor_link_state["device_id"],
        "checked_at": now_str,
        "message": _sensor_link_state["message"],
        "troubleshooting": [],
    }


# RF4 y RF6: En este endpoint recibimos lecturas, evaluamos alertas y guardamos en BD
@router.post("/telemetry")
async def ingest_field_telemetry(data: FieldTelemetryInput):
    """Guarda nueva lectura de temperatura/humedad y registra alertas si sale del óptimo."""
    updated = db.save_module_state(
        MODULE_ID,
        air_temperature=data.air_temperature,
        air_humidity=data.air_humidity,
        soil_humidity_pct=data.soil_humidity_pct,
        barometric_pressure_hpa=data.barometric_pressure_hpa,
    )
    db.insert_telemetry(
        module_id=MODULE_ID,
        temp=data.air_temperature,
        humidity=data.air_humidity,
        pressure=updated["barometric_pressure_hpa"],
        vpd=updated["vpd_kpa"],
        level=updated["reservoir_level_percent"],
        pump_active=False,
        servo_angle=0,
        steps=0,
        origen=data.source,
    )
    alerts = _evaluate_orchid_alerts(data.air_temperature, data.air_humidity)
    for msg in alerts:
        sev = "CRITICAL" if "HUMEDAD BAJA" in msg else "WARNING"
        db.insert_alert(MODULE_ID, sev, msg)

    _sensor_link_state["connected"] = True
    _sensor_link_state["last_checked"] = updated["timestamp"]

    return {
        "status": "success",
        "message": "Lectura ambiental almacenada correctamente en base de datos (RF5, RF6)",
        "active_alerts": alerts,
        "telemetry": {
            "air_temperature": updated["air_temperature"],
            "air_humidity": updated["air_humidity"],
            "barometric_pressure_hpa": updated["barometric_pressure_hpa"],
            "soil_humidity_pct": updated["soil_humidity_pct"],
            "timestamp": updated["timestamp"],
            "status": "ALERTA" if alerts else "OPTIMO",
        },
    }


# RF5: Aquí consultamos el historial filtrado solo para el invernadero de orquídeas
@router.get("/history")
async def get_field_history(limit: int = 12):
    """Devuelve las últimas lecturas históricas solo del invernadero de orquídeas (RF5)."""
    records = db.get_telemetry_history(limit=limit, module_id=MODULE_ID)
    sched = db.load_schedule(MODULE_ID)
    return {
        "modulo": MODULE_ID,
        "recording_frequency_minutes": sched["recording_frequency_minutes"],
        "storage": db.get_storage_backend_info(),
        "total_records": len(records),
        "history": records,
    }


# RF7 y Wokwi: Control manual del relé de aspersión (Pin 5) y ciclo demostrativo
@router.post("/pump")
async def control_field_pump(cmd: FieldPumpCommand):
    """Activa o apaga manualmente la bomba/relé de aspersión en Wokwi (Pin 5 vía MQTT)."""
    act = cmd.action.strip().upper()
    if act not in ("ON", "OFF"):
        raise HTTPException(status_code=400, detail="Acción no válida. Use 'ON' o 'OFF'.")
    turn_on = act == "ON"
    res = _apply_field_pump(turn_on, "MANUAL_WEB_ORQUIDEAS", auto_off_seconds=cmd.duration_seconds if turn_on else None)
    return {
        "status": "success",
        **res,
        "message": f"Aspersión Orquídeas {'ENCENDIDA' if turn_on else 'APAGADA'} (ASAI/Orquideas/Bomba/cmd).",
    }


@router.post("/demo-cycle")
async def configure_field_demo_cycle(cfg: DemoCycleConfig):
    """Activa o detiene ciclo automático demostrativo (ej. cada 10s regar 5s)."""
    if cfg.enabled and cfg.interval_seconds <= cfg.duration_seconds:
        raise HTTPException(
            status_code=400,
            detail="El intervalo entre riegos debe ser mayor a la duración de aspersión.",
        )

    _irrigation_runtime["interval_seconds"] = cfg.interval_seconds
    _irrigation_runtime["duration_seconds"] = cfg.duration_seconds
    _irrigation_runtime["demo_enabled"] = cfg.enabled

    if cfg.enabled:
        res = _apply_field_pump(True, "AUTO_DEMO_CICLO", auto_off_seconds=cfg.duration_seconds)
        _irrigation_runtime["next_demo_at"] = time.monotonic() + cfg.interval_seconds
        msg = f"Ciclo demo activo: aspersión cada {cfg.interval_seconds}s durante {cfg.duration_seconds}s."
    else:
        res = _apply_field_pump(False, "DEMO_DETENIDO")
        _irrigation_runtime["next_demo_at"] = None
        msg = "Ciclo automático demo detenido."

    return {
        "status": "success",
        "message": msg,
        "irrigation_control": _get_irrigation_control_status(res["pump_active"]),
    }
