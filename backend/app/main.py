import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import db
from app.config import settings
from app.mqtt_bridge import mqtt_bridge
from app.models import (
    PlantProfile,
    HydroponicModule,
    TelemetryInput,
    ActuatorCommand,
    JevDecisionResponse,
    FarmChatRequest,
    FarmChatResponse,
    HealthStatus
)
from app.routers import field_service, home_tower_service, vertical_farm_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de FastAPI: inicia y apaga el puente MQTT y planificador de Orquídeas."""
    mqtt_bridge.start()
    field_service.start_orchid_scheduler()
    try:
        yield
    finally:
        await field_service.stop_orchid_scheduler()
        mqtt_bridge.stop()

app = FastAPI(
    title="AgroSense AI — Core Management Hub (SOA Tri-Servicio)",
    description="Hub SOA para: 1. AgroField (Orquídeas IEI-094), 2. HomeTower (Mini Torres Feria Innovación & Android), 3. VerticalFarm (Invernaderos Industriales)",
    version="2.2.0",
    lifespan=lifespan,
)

# Montaje de Routers de Servicios Desacoplados (SOA)
app.include_router(field_service.router, prefix="/api/v1/services/field", tags=["1. AgroField Service (Integración II - Orquídeas)"])
app.include_router(home_tower_service.router, prefix="/api/v1/services/home-tower", tags=["2. HomeTower Service (Feria Innovación - Mini Torre)"])
app.include_router(vertical_farm_service.router, prefix="/api/v1/services/vertical-farm", tags=["3. VerticalFarm Service (Invernaderos Industriales)"])

# Configuración de templates HTML y Base de Datos SQLite compartida
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)
db.init_db()


# ==============================================================================
# HELPERS DE ESTADO PERSISTENTE Y MODELOS DE BANDEJA
# ==============================================================================

current_plant_profile = PlantProfile(
    id="crop_frutilla_hidroponica",
    species_name="Frutilla Hidropónica (Fragaria x ananassa)",
    variety="Albion / San Andreas",
    optimal_temp_min_c=18.0,
    optimal_temp_max_c=24.0,
    optimal_humidity_min=55.0,
    optimal_humidity_max=75.0,
    optimal_vpd_min_kpa=0.8,
    optimal_vpd_max_kpa=1.2,
    recirculation_cycle_minutes=15,
    recirculation_interval_hours=2,
    researched_by_llm=True
)

current_module = HydroponicModule(
    id="celda-01",
    name="Mini Torre Domiciliaria ASAI (Celda 01)",
    location="Santo Tomás Temuco - Laboratorio IoT",
    plant_profile_id=current_plant_profile.id,
    growth_stage="FLORACION",
    active=True
)

recent_commands: List[ActuatorCommand] = []


def _get_live_telemetry() -> TelemetryInput:
    """Construye TelemetryInput desde el estado persistente en SQLite."""
    state = db.load_module_state(current_module.id)
    return TelemetryInput(
        module_id=current_module.id,
        air_temperature=state["air_temperature"],
        air_humidity=state["air_humidity"],
        barometric_pressure_hpa=state["barometric_pressure_hpa"],
        reservoir_level_percent=state["reservoir_level_percent"],
        vpd_kpa=state["vpd_kpa"],
        pump_active=state["pump_active"],
        vent_servo_angle=state["vent_servo_angle"],
        stepper_dosing_steps=state["stepper_dosing_steps"],
    )


def _get_live_profile() -> PlantProfile:
    """Sincroniza el perfil de cultivo con la configuración persistida en SQLite."""
    sched = db.load_schedule(current_module.id)
    current_plant_profile.recirculation_interval_hours = sched["interval_hours"]
    current_plant_profile.recirculation_cycle_minutes = sched["duration_minutes"]
    return current_plant_profile


def _build_schedule_summary(telemetry: TelemetryInput) -> Dict[str, Any]:
    """Calcula resumen semanal y próximo ciclo desde calendario_semanal en SQLite."""
    sched = db.load_schedule(current_module.id)
    hoy_str = db.get_today_es()
    active_days = sched["active_days"] or ["Lun"]
    prox_dia = hoy_str if hoy_str in active_days else active_days[0]
    next_cycle = datetime.now() + timedelta(hours=sched["interval_hours"])
    return {
        "interval_hours": sched["interval_hours"],
        "duration_minutes": sched["duration_minutes"],
        "active_days": active_days,
        "dias_semana": sched["dias_semana"],
        "today_str": hoy_str,
        "irrigation_time": sched["irrigation_time"],
        "next_cycle_time": next_cycle.strftime("%H:%M:%S"),
        "next_cycle_full": next_cycle.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "BOMBEANDO" if telemetry.pump_active else "EN_ESPERA",
        "notification": (
            f"Próximo riego programado para {prox_dia} a las {sched['irrigation_time']} hrs "
            f"({sched['duration_minutes']} min). Días activos: {', '.join(active_days)}."
        ),
    }


# ==============================================================================
# MOTOR DETERMINISTA DE RESPALDO (LOCAL FALLBACK - CIBERFÍSICO)
# ==============================================================================

def evaluate_jev_local(telemetry: TelemetryInput, profile: PlantProfile) -> JevDecisionResponse:
    # 1. Regla Crítica: Protección contra cavitación
    if telemetry.reservoir_level_percent < 20.0:
        return JevDecisionResponse(
            action_required=True,
            recommended_pump_state=False,
            recommended_vent_angle=telemetry.vent_servo_angle,
            reason=f"BLOQUEO DE SEGURIDAD: Nivel de estanque crítico ({telemetry.reservoir_level_percent:.1f}% < 20.0%). Bomba 5V apagada inmediatamente para evitar sobrecalentamiento y cavitación.",
            risk_level="CRITICAL",
            execution_time_ms=12.0,
            fallback_rule_applied=True
        )

    # 2. Regla Térmica: Ventilación Cenital Servo SG90
    dpv = telemetry.vpd_kpa or db.calculate_vpd(telemetry.air_temperature, telemetry.air_humidity)
    if telemetry.air_temperature > profile.optimal_temp_max_c or dpv > profile.optimal_vpd_max_kpa:
        return JevDecisionResponse(
            action_required=True,
            recommended_pump_state=telemetry.pump_active,
            recommended_vent_angle=90,
            reason=f"ALIVIO TÉRMICO ACTIVO: Temperatura ({telemetry.air_temperature:.1f}°C) o DPV ({dpv:.2f} kPa) superan el umbral óptimo del cultivo ({profile.optimal_temp_max_c}°C / {profile.optimal_vpd_max_kpa} kPa). Servomotor abre ventilación a 90°.",
            risk_level="WARNING",
            execution_time_ms=15.0,
            fallback_rule_applied=True
        )

    # 3. Estado Óptimo
    return JevDecisionResponse(
        action_required=False,
        recommended_pump_state=telemetry.pump_active,
        recommended_vent_angle=0,
        reason=f"CONDICIONES ÓPTIMAS: Nivel ({telemetry.reservoir_level_percent:.1f}%), Temp ({telemetry.air_temperature:.1f}°C) y DPV ({dpv:.2f} kPa) en rangos ideales para {profile.species_name}.",
        risk_level="NORMAL",
        execution_time_ms=8.0,
        fallback_rule_applied=True
    )


async def evaluate_jev(telemetry: TelemetryInput, profile: PlantProfile) -> JevDecisionResponse:
    api_key = settings.LLM_API_KEY.strip()
    api_error_notice = None

    if api_key and api_key != "tu_api_key_aqui" and not api_key.startswith("dev_local_key"):
        try:
            url = settings.JEV_DECISIONS_API_URL
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agrosense.ai",
                "X-Title": "AgroSense AI - Hydroponic Cell Decisions"
            }
            state = {
                "module_id": telemetry.module_id,
                "crop": profile.species_name,
                "air_temp_c": telemetry.air_temperature,
                "air_humidity_pct": telemetry.air_humidity,
                "reservoir_level_pct": telemetry.reservoir_level_percent,
                "barometric_pressure_hpa": telemetry.barometric_pressure_hpa,
                "pump_active": telemetry.pump_active
            }
            questions = {
                "activate_action": {"type": "noul", "instructions": "¿Se requiere conmutar algún actuador físico de la bandeja?"},
                "dispatched_tool": {"type": "choice", "instructions": "¿Qué actuador debe responder?", "options": ["ninguno", "bomba_agua", "servo_ventilacion", "motor_nutrientes"]}
            }
            payload = {"model": settings.JEV_MODEL_NAME, "state": state, "questions": questions}
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    decisions = data.get("decisions", {})
                    is_active = decisions.get("activate_action", {}).get("value", False)
                    tool = decisions.get("dispatched_tool", {}).get("value", "ninguno")
                    return JevDecisionResponse(
                        action_required=bool(is_active),
                        recommended_pump_state=True if tool == "bomba_agua" and is_active else False,
                        recommended_vent_angle=90 if tool == "servo_ventilacion" and is_active else 0,
                        reason=f"Decisión IA emitida por TypeSafe Jev ({settings.JEV_MODEL_NAME}): Actuador sugerido: '{tool}'. Inferencia completada en la nube.",
                        risk_level="NORMAL",
                        execution_time_ms=80.0,
                        fallback_rule_applied=False
                    )
                else:
                    api_error_notice = f"⚠️ [Aviso Jev Cloud HTTP {res.status_code}]: Conmutando a reglas locales deterministas. "
        except Exception as e:
            api_error_notice = f"⚠️ [Aviso Jev Cloud ({type(e).__name__})]: Conmutando a reglas locales deterministas. "

    fallback = evaluate_jev_local(telemetry, profile)
    if api_error_notice:
        fallback.reason = f"{api_error_notice}{fallback.reason}"
    return fallback


SCENARIO_PRESETS: Dict[str, Dict[str, Any]] = {
    "estanque_vacio": {"reservoir_level_percent": 12.0, "pump_active": False},
    "calor_extremo": {"air_temperature": 28.5, "air_humidity": 42.0},
    "optimo": {"reservoir_level_percent": 85.0, "air_temperature": 21.5, "air_humidity": 62.0, "vpd_kpa": 0.95, "vent_servo_angle": 0},
    "recirculacion": {"reservoir_level_percent": 80.0, "pump_active": True},
}


# ==============================================================================
# ENDPOINTS REST DE LA API (SOA)
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Sirve el Dashboard Web interactivo y adaptativo de AgroSense AI (SOA Tri-Servicio):
    1. AgroField Service (Invernadero & Orquídeas - Integración II)
    2. HomeTower Service (Mini Torres Domiciliarias - Feria de Innovación & Android)
    3. VerticalFarm Service (Invernaderos Industriales)
    """
    live_tel = _get_live_telemetry()
    live_prof = _get_live_profile()
    live_jev = evaluate_jev_local(live_tel, live_prof)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "module": current_module,
            "plant": live_prof,
            "telemetry": live_tel,
            "jev": live_jev,
            "schedule": _build_schedule_summary(live_tel),
            "history": db.get_telemetry_history(limit=12, module_id="invernadero-orquideas"),
            "storage_info": db.get_storage_backend_info(),
            "recent_commands": recent_commands[-5:],
            "field_data": field_service.get_field_dashboard_data(),
            "home_tower_data": home_tower_service.get_home_tower_dashboard_data(),
            "vertical_farm_data": {
                "racks": vertical_farm_service.INDUSTRIAL_RACKS
            },
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    )


@app.get("/api/v1/health", response_model=HealthStatus)
async def health_check():
    return HealthStatus(
        status="healthy",
        environment=settings.ENVIRONMENT,
        hardware_target="ESP32 DevKit V1 (DHT11 + BME280 + Nivel + 3 Actuadores)"
    )


@app.post("/api/v1/telemetry", response_model=Dict[str, Any])
async def ingest_telemetry(telemetry: TelemetryInput):
    """
    Ingesta de telemetría IoT desde el ESP32:
    1. Calcula DPV si no viene incluido.
    2. Actualiza estado operativo persistente y guarda en telemetria_historica (SQLite).
    3. Evalúa reglas ciberfísicas de JEV.
    """
    if not telemetry.vpd_kpa:
        telemetry.vpd_kpa = db.calculate_vpd(telemetry.air_temperature, telemetry.air_humidity)

    db.save_module_state(
        telemetry.module_id,
        air_temperature=telemetry.air_temperature,
        air_humidity=telemetry.air_humidity,
        barometric_pressure_hpa=telemetry.barometric_pressure_hpa,
        reservoir_level_percent=telemetry.reservoir_level_percent,
        vpd_kpa=telemetry.vpd_kpa,
        pump_active=telemetry.pump_active,
        vent_servo_angle=telemetry.vent_servo_angle,
        stepper_dosing_steps=telemetry.stepper_dosing_steps,
    )
    db.insert_telemetry(
        module_id=telemetry.module_id,
        temp=telemetry.air_temperature,
        humidity=telemetry.air_humidity,
        pressure=telemetry.barometric_pressure_hpa,
        vpd=telemetry.vpd_kpa,
        level=telemetry.reservoir_level_percent,
        pump_active=telemetry.pump_active,
        servo_angle=telemetry.vent_servo_angle,
        steps=telemetry.stepper_dosing_steps,
        origen="REST_ESP32",
    )

    jev_decision = await evaluate_jev(telemetry, _get_live_profile())
    return {
        "status": "success",
        "message": "Telemetría guardada en SQLite e inferencia evaluada con éxito",
        "telemetry": telemetry,
        "jev_decision": jev_decision
    }


@app.get("/api/v1/telemetry/latest", response_model=TelemetryInput)
async def get_latest_telemetry():
    return _get_live_telemetry()


@app.get("/api/v1/telemetry/history")
async def get_telemetry_history(limit: int = 20):
    """Retorna las lecturas históricas guardadas en la base de datos relacional."""
    return db.get_telemetry_history(limit=limit)


@app.post("/api/v1/actuators/command", response_model=Dict[str, Any])
async def send_actuator_command(cmd: ActuatorCommand):
    recent_commands.append(cmd)
    home_tower_service.apply_actuator_command_persistent(
        module_id=cmd.module_id or current_module.id,
        target=cmd.target,
        action=cmd.action,
        parameter_value=cmd.parameter_value,
        triggered_by=cmd.triggered_by,
        enforce_cavitation_lock=True,
    )
    mqtt_published = mqtt_bridge.publish_actuator_command(
        target=cmd.target,
        action=cmd.action,
        parameter_value=cmd.parameter_value,
    )
    return {
        "status": "command_registered",
        "actuator": cmd.target,
        "action": cmd.action,
        "parameter_value": cmd.parameter_value,
        "triggered_by": cmd.triggered_by,
        "mqtt_published": bool(mqtt_published),
        "message": f"Comando '{cmd.action}' registrado y guardado en base de datos para {cmd.target}."
    }


class ScheduleUpdateRequest(BaseModel):
    interval_hours: int = Field(default=2, ge=1, le=24, description="Frecuencia en horas entre ciclos")
    duration_minutes: int = Field(default=15, ge=1, le=120, description="Duración de bombeo en minutos")
    active_days: Optional[List[str]] = Field(default=None, description="Días activos de la semana (RF1)")
    irrigation_time: Optional[str] = Field(default=None, description="Hora de riego programada (RF1)")


@app.get("/api/v1/schedule", response_model=Dict[str, Any])
async def get_schedule():
    """Endpoint de calendario de recirculación persistente (Cumple RF1 y RF2 IEI-094)."""
    live_tel = _get_live_telemetry()
    summary = _build_schedule_summary(live_tel)
    return {
        "module_id": current_module.id,
        "crop": current_plant_profile.species_name,
        "active_days": summary["active_days"],
        "irrigation_time": summary["irrigation_time"],
        "recirculation_duration_minutes": summary["duration_minutes"],
        "interval_hours": summary["interval_hours"],
        "next_cycle": summary["next_cycle_full"],
        "pump_status": "ACTIVA" if live_tel.pump_active else "EN_ESPERA",
        "notification_message": summary["notification"],
    }


@app.post("/api/v1/schedule", response_model=Dict[str, Any])
async def update_schedule(data: ScheduleUpdateRequest):
    """
    Actualiza la configuración del calendario de riego/recirculación:
    Persiste en SQLite (calendario_semanal y perfiles_cultivo).
    """
    db.save_schedule(
        current_module.id,
        active_days=data.active_days,
        irrigation_time=data.irrigation_time,
        duration_minutes=data.duration_minutes,
        interval_hours=data.interval_hours,
    )
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE perfiles_cultivo SET intervalo_riego_horas = ?, recirculacion_minutos = ? WHERE id = 1",
            (data.interval_hours, data.duration_minutes),
        )
        conn.commit()

    summary = _build_schedule_summary(_get_live_telemetry())
    return {
        "status": "success",
        "message": (
            f"Calendario guardado en BD: Días [{', '.join(summary['active_days'])}] a las "
            f"{summary['irrigation_time']} hrs (Ciclo cada {data.interval_hours}h por {data.duration_minutes} min)."
        ),
        "interval_hours": summary["interval_hours"],
        "duration_minutes": summary["duration_minutes"],
        "active_days": summary["active_days"],
        "irrigation_time": summary["irrigation_time"],
        "notification": summary["notification"],
    }


@app.post("/api/v1/simulate/{scenario}")
async def simulate_scenario(scenario: str):
    preset = SCENARIO_PRESETS.get(scenario)
    if preset is None:
        raise HTTPException(status_code=400, detail="Escenario no reconocido.")

    updated = db.save_module_state(current_module.id, **preset)
    db.insert_telemetry(
        module_id=current_module.id,
        temp=updated["air_temperature"],
        humidity=updated["air_humidity"],
        pressure=updated["barometric_pressure_hpa"],
        vpd=updated["vpd_kpa"],
        level=updated["reservoir_level_percent"],
        pump_active=updated["pump_active"],
        servo_angle=updated["vent_servo_angle"],
        steps=updated["stepper_dosing_steps"],
        origen=f"SIMULACION_{scenario.upper()}",
    )

    live_tel = _get_live_telemetry()
    jev_decision = await evaluate_jev(live_tel, _get_live_profile())
    return {
        "scenario": scenario,
        "telemetry": live_tel,
        "jev_decision": jev_decision,
    }


@app.post("/api/v1/chat/farm", response_model=FarmChatResponse)
async def chat_with_farm(request: FarmChatRequest):
    tools_used = ["DHT11", "BME280", "SensorNivelResistivo", "SQLiteHistory", "JevDecisionLog"]
    live_tel = _get_live_telemetry()
    live_prof = _get_live_profile()
    live_jev = evaluate_jev_local(live_tel, live_prof)

    system_prompt = f"""Eres el Asistente Agronómico Inteligente de la plataforma 'AgroSense AI'.
Estás a cargo de la celda hidropónica piloto '{current_module.name}'.
Responde de forma profesional, concisa, técnica y empática basándote en los datos reales del hardware y la base de datos.

DATOS DE LA BANDEJA HIDROPÓNICA:
- Cultivo: {live_prof.species_name} ({live_prof.variety})
- Rango óptimo Temp: {live_prof.optimal_temp_min_c}°C a {live_prof.optimal_temp_max_c}°C
- Rango óptimo Humedad: {live_prof.optimal_humidity_min}% a {live_prof.optimal_humidity_max}%
- DPV óptimo: {live_prof.optimal_vpd_min_kpa} a {live_prof.optimal_vpd_max_kpa} kPa

MEDICIONES REALES EN TIEMPO REAL:
- Temp ambiental: {live_tel.air_temperature} °C
- Humedad aérea: {live_tel.air_humidity} %
- Presión barométrica: {live_tel.barometric_pressure_hpa} hPa
- DPV: {live_tel.vpd_kpa} kPa
- Nivel de estanque: {live_tel.reservoir_level_percent} %
- Bomba 5V: {'ENCENDIDA' if live_tel.pump_active else 'APAGADA'}
- Servo Cenital: {live_tel.vent_servo_angle}°
- Decisión JEV: {live_jev.reason}
"""

    api_key = settings.LLM_API_KEY.strip()
    api_error_notice = None

    if api_key and api_key != "tu_api_key_aqui" and not api_key.startswith("dev_local_key"):
        try:
            url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agrosense.ai",
                "X-Title": "AgroSense AI Hydroponic Chat"
            }
            payload = {
                "model": settings.LLM_MODEL_NAME,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.question}
                ],
                "temperature": 0.3,
                "max_tokens": 400
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    ai_answer = data["choices"][0]["message"]["content"]
                    return FarmChatResponse(
                        answer=ai_answer,
                        tools_consulted=tools_used + [f"DeepSeek ({settings.LLM_MODEL_NAME})"],
                        model_used=settings.LLM_MODEL_NAME
                    )
                else:
                    api_error_notice = f"⚠️ [Aviso: Fallo API externa HTTP {res.status_code} - Modo Local Activado]:\n"
        except Exception as e:
            api_error_notice = f"⚠️ [Aviso: Error conexión ({type(e).__name__}) - Modo Local Activado]:\n"
    else:
        api_error_notice = "⚠️ [Aviso: Clave LLM no configurada - Respuesta heurística local]:\n"

    # Respuesta Heurística Local
    q = request.question.lower()
    if any(k in q for k in ("bomba", "riego", "estanque", "calendario")):
        answer = (
            f"El estanque reporta un nivel del {live_tel.reservoir_level_percent:.1f}%. "
            f"La mini-bomba sumergible de 5V se encuentra {'ENCENDIDA recirculando' if live_tel.pump_active else 'APAGADA en ciclo de espera'}. "
            f"Programación: ciclos de {live_prof.recirculation_cycle_minutes} min cada {live_prof.recirculation_interval_hours} horas. "
            f"Evaluación JEV: {live_jev.reason}"
        )
    elif any(k in q for k in ("temperatura", "humedad", "clima", "dpv")):
        answer = (
            f"Temperatura ambiental: {live_tel.air_temperature:.1f}°C, humedad: {live_tel.air_humidity:.1f}%. "
            f"El Déficit de Presión de Vapor (DPV) es {live_tel.vpd_kpa:.2f} kPa. "
            f"Ventilación cenital servo a {live_tel.vent_servo_angle}°."
        )
    else:
        answer = (
            f"Hola, soy el asistente de la Celda Hidropónica Piloto 01 ({live_prof.species_name}). "
            f"Estado {live_jev.risk_level}: Temp {live_tel.air_temperature:.1f}°C, "
            f"Humedad {live_tel.air_humidity:.1f}%, Estanque al {live_tel.reservoir_level_percent:.1f}%. "
            f"Cada lectura se está guardando activamente en la base de datos relacional SQLite."
        )

    if api_error_notice:
        answer = f"{api_error_notice}{answer}"

    return FarmChatResponse(
        answer=answer,
        tools_consulted=tools_used + ["Motor Local Heurístico"],
        model_used="local-heuristics"
    )
