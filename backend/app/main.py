import os
import sqlite3
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
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

app = FastAPI(
    title="AgroSense AI — Core Management Hub (SOA)",
    description="Microservicio Hub para Ingesta IoT (ESP32), Persistencia SQLite, Orquestación JEV, Control de Actuadores y Asistente Agronómico",
    version="2.1.0"
)

# Configuración de templates HTML y Base de Datos SQLite
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "agrosense.db")

# ==============================================================================
# INICIALIZACIÓN Y PERSISTENCIA EN BASE DE DATOS SQLITE
# ==============================================================================

def init_db():
    """Crea las tablas a partir de database_schema.sql e inserta datos iniciales si está vacía."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    schema_path = os.path.join(os.path.dirname(__file__), "database_schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            cursor.executescript(f.read())
    
    # Verificar si hay datos históricos; si no, insertar lecturas iniciales de prueba
    cursor.execute("SELECT COUNT(*) FROM telemetria_historica")
    count = cursor.fetchone()[0]
    if count == 0:
        ahora = datetime.utcnow()
        seed_data = [
            ("celda-01", (ahora - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S"), 21.2, 64.0, 1014.0, 0.92, 88.0, 0, 0, 0),
            ("celda-01", (ahora - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"), 21.6, 63.1, 1014.2, 0.95, 86.5, 1, 0, 0),
            ("celda-01", ahora.strftime("%Y-%m-%d %H:%M:%S"), 21.8, 62.4, 1014.5, 0.98, 85.0, 0, 0, 0),
        ]
        cursor.executemany("""
            INSERT INTO telemetria_historica (
                modulo_id, fecha_hora, temp_ambiente, humedad_ambiente, presion_atmosferica,
                dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo, pasos_motor_acumulados
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_data)
        conn.commit()

    conn.close()

# Inicializar BD al arrancar
init_db()

def save_telemetry_to_db(t: TelemetryInput):
    """Guarda cada lectura física emitida por el ESP32 en la base de datos relacional."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO telemetria_historica (
            modulo_id, temp_ambiente, humedad_ambiente, presion_atmosferica,
            dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo, pasos_motor_acumulados
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        t.module_id, t.air_temperature, t.air_humidity, t.barometric_pressure_hpa,
        t.vpd_kpa, t.reservoir_level_percent, 1 if t.pump_active else 0,
        t.vent_servo_angle, t.stepper_dosing_steps
    ))
    conn.commit()
    conn.close()

def save_command_to_db(cmd: ActuatorCommand):
    """Guarda en auditoría cada orden ejecutada sobre los actuadores."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO registro_comandos (
            modulo_id, actuador, accion, parametro_valor, disparado_por
        ) VALUES (?, ?, ?, ?, ?)
    """, (cmd.module_id, cmd.target, cmd.action, cmd.parameter_value, cmd.triggered_by))
    conn.commit()
    conn.close()

def get_recent_history(limit: int = 8) -> List[Dict[str, Any]]:
    """Obtiene las últimas mediciones para mostrar en el dashboard web y la app móvil."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, fecha_hora, temp_ambiente, humedad_ambiente, presion_atmosferica,
               dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo
        FROM telemetria_historica
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# ==============================================================================
# ESTADO EN MEMORIA Y MODELOS DE BANDEJA
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
    name="Bandeja Hidropónica Piloto - Frutilla",
    location="Santo Tomás Temuco - Laboratorio IoT",
    plant_profile_id=current_plant_profile.id,
    growth_stage="FLORACION",
    active=True
)

latest_telemetry = TelemetryInput(
    module_id=current_module.id,
    air_temperature=21.8,
    air_humidity=62.4,
    barometric_pressure_hpa=1014.5,
    reservoir_level_percent=85.0,
    vpd_kpa=0.98,
    pump_active=False,
    vent_servo_angle=0,
    stepper_dosing_steps=0
)

recent_commands: List[ActuatorCommand] = []


# ==============================================================================
# MOTOR DETERMINISTA DE RESPALDO (LOCAL FALLBACK - CIBERFÍSICO)
# ==============================================================================

def calculate_vpd(temp_c: float, rh_pct: float) -> float:
    """Fórmula de Tetens para el Déficit de Presión de Vapor (DPV) en kPa."""
    svp = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    avp = svp * (rh_pct / 100.0)
    return round(svp - avp, 2)


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
    dpv = telemetry.vpd_kpa or calculate_vpd(telemetry.air_temperature, telemetry.air_humidity)
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


latest_jev_decision = evaluate_jev_local(latest_telemetry, current_plant_profile)


# ==============================================================================
# ENDPOINTS REST DE LA API (SOA)
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Sirve el Dashboard Web interactivo de la Celda Hidropónica Piloto 01
    incluyendo el Calendario de Riego y el Histórico de la Base de Datos.
    """
    history_records = get_recent_history(limit=8)
    
    # Calcular próximo ciclo de riego
    next_cycle = datetime.now() + timedelta(hours=current_plant_profile.recirculation_interval_hours)
    schedule_data = {
        "interval_hours": current_plant_profile.recirculation_interval_hours,
        "duration_minutes": current_plant_profile.recirculation_cycle_minutes,
        "next_cycle_time": next_cycle.strftime("%H:%M:%S"),
        "status": "BOMBEANDO" if latest_telemetry.pump_active else "EN_ESPERA",
        "notification": "Riego programado activo: 15 min cada 2 horas."
    }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "module": current_module,
            "plant": current_plant_profile,
            "telemetry": latest_telemetry,
            "jev": latest_jev_decision,
            "schedule": schedule_data,
            "history": history_records,
            "recent_commands": recent_commands[-5:],
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
    2. Guarda permanentemente en la base de datos SQLite (Histórico).
    3. Evalúa reglas ciberfísicas de JEV.
    """
    global latest_telemetry, latest_jev_decision
    if not telemetry.vpd_kpa:
        telemetry.vpd_kpa = calculate_vpd(telemetry.air_temperature, telemetry.air_humidity)
    
    latest_telemetry = telemetry
    
    # PERSISTENCIA EN SQLITE
    save_telemetry_to_db(latest_telemetry)
    
    latest_jev_decision = await evaluate_jev(latest_telemetry, current_plant_profile)
    return {
        "status": "success",
        "message": "Telemetría guardada en SQLite e inferencia evaluada con éxito",
        "telemetry": latest_telemetry,
        "jev_decision": latest_jev_decision
    }


@app.get("/api/v1/telemetry/latest", response_model=TelemetryInput)
async def get_latest_telemetry():
    return latest_telemetry


@app.get("/api/v1/telemetry/history")
async def get_telemetry_history(limit: int = 20):
    """Retorna las lecturas históricas guardadas en la base de datos relacional."""
    return get_recent_history(limit=limit)


@app.post("/api/v1/actuators/command", response_model=Dict[str, Any])
async def send_actuator_command(cmd: ActuatorCommand):
    global latest_telemetry, recent_commands
    recent_commands.append(cmd)
    
    # GUARDAR AUDITORÍA DE COMANDOS EN SQLITE
    save_command_to_db(cmd)

    if cmd.target == "bomba_agua":
        latest_telemetry.pump_active = (cmd.action.upper() == "ON")
    elif cmd.target == "servo_ventilacion":
        latest_telemetry.vent_servo_angle = int(cmd.parameter_value or 0)
    elif cmd.target == "motor_nutrientes":
        latest_telemetry.stepper_dosing_steps += int(cmd.parameter_value or 0)

    # Actualizar BD con el nuevo estado del actuador
    save_telemetry_to_db(latest_telemetry)

    return {
        "status": "command_registered",
        "actuator": cmd.target,
        "action": cmd.action,
        "parameter_value": cmd.parameter_value,
        "triggered_by": cmd.triggered_by,
        "message": f"Comando '{cmd.action}' registrado y guardado en base de datos para {cmd.target}."
    }


@app.get("/api/v1/schedule", response_model=Dict[str, Any])
async def get_schedule():
    """Endpoint de calendario de recirculación (Requerimiento Semana 13 Integración II)."""
    next_cycle = datetime.now() + timedelta(hours=current_plant_profile.recirculation_interval_hours)
    return {
        "module_id": current_module.id,
        "crop": current_plant_profile.species_name,
        "recirculation_duration_minutes": current_plant_profile.recirculation_cycle_minutes,
        "interval_hours": current_plant_profile.recirculation_interval_hours,
        "next_cycle": next_cycle.strftime("%Y-%m-%d %H:%M:%S"),
        "pump_status": "ACTIVA" if latest_telemetry.pump_active else "EN_ESPERA",
        "notification_message": f"Próximo ciclo programado a las {next_cycle.strftime('%H:%M:%S')} ({current_plant_profile.recirculation_cycle_minutes} min)"
    }


@app.post("/api/v1/simulate/{scenario}")
async def simulate_scenario(scenario: str):
    global latest_telemetry, latest_jev_decision

    if scenario == "estanque_vacio":
        latest_telemetry.reservoir_level_percent = 12.0
        latest_telemetry.pump_active = False
    elif scenario == "calor_extremo":
        latest_telemetry.air_temperature = 28.5
        latest_telemetry.air_humidity = 42.0
        latest_telemetry.vpd_kpa = calculate_vpd(28.5, 42.0)
    elif scenario == "optimo":
        latest_telemetry.reservoir_level_percent = 85.0
        latest_telemetry.air_temperature = 21.5
        latest_telemetry.air_humidity = 62.0
        latest_telemetry.vpd_kpa = 0.95
        latest_telemetry.vent_servo_angle = 0
    elif scenario == "recirculacion":
        latest_telemetry.reservoir_level_percent = 80.0
        latest_telemetry.pump_active = True
    else:
        raise HTTPException(status_code=400, detail="Escenario no reconocido.")

    save_telemetry_to_db(latest_telemetry)
    latest_jev_decision = await evaluate_jev(latest_telemetry, current_plant_profile)
    return {
        "scenario": scenario,
        "telemetry": latest_telemetry,
        "jev_decision": latest_jev_decision
    }


@app.post("/api/v1/chat/farm", response_model=FarmChatResponse)
async def chat_with_farm(request: FarmChatRequest):
    tools_used = ["DHT11", "BME280", "SensorNivelResistivo", "SQLiteHistory", "JevDecisionLog"]

    system_prompt = f"""Eres el Asistente Agronómico Inteligente de la plataforma 'AgroSense AI'.
Estás a cargo de la celda hidropónica piloto '{current_module.name}'.
Responde de forma profesional, concisa, técnica y empática basándote en los datos reales del hardware y la base de datos.

DATOS DE LA BANDEJA HIDROPÓNICA:
- Cultivo: {current_plant_profile.species_name} ({current_plant_profile.variety})
- Rango óptimo Temp: {current_plant_profile.optimal_temp_min_c}°C a {current_plant_profile.optimal_temp_max_c}°C
- Rango óptimo Humedad: {current_plant_profile.optimal_humidity_min}% a {current_plant_profile.optimal_humidity_max}%
- DPV óptimo: {current_plant_profile.optimal_vpd_min_kpa} a {current_plant_profile.optimal_vpd_max_kpa} kPa

MEDICIONES REALES EN TIEMPO REAL:
- Temp ambiental: {latest_telemetry.air_temperature} °C
- Humedad aérea: {latest_telemetry.air_humidity} %
- Presión barométrica: {latest_telemetry.barometric_pressure_hpa} hPa
- DPV: {latest_telemetry.vpd_kpa} kPa
- Nivel de estanque: {latest_telemetry.reservoir_level_percent} %
- Bomba 5V: {'ENCENDIDA' if latest_telemetry.pump_active else 'APAGADA'}
- Servo Cenital: {latest_telemetry.vent_servo_angle}°
- Decisión JEV: {latest_jev_decision.reason}
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
    if "bomba" in q or "riego" in q or "estanque" in q or "calendario" in q:
        answer = (
            f"El estanque reporta un nivel del {latest_telemetry.reservoir_level_percent:.1f}%. "
            f"La mini-bomba sumergible de 5V se encuentra {'ENCENDIDA recirculando' if latest_telemetry.pump_active else 'APAGADA en ciclo de espera'}. "
            f"Programación: ciclos de {current_plant_profile.recirculation_cycle_minutes} min cada {current_plant_profile.recirculation_interval_hours} horas. "
            f"Evaluación JEV: {latest_jev_decision.reason}"
        )
    elif "temperatura" in q or "humedad" in q or "clima" in q or "dpv" in q:
        answer = (
            f"Temperatura ambiental: {latest_telemetry.air_temperature:.1f}°C, humedad: {latest_telemetry.air_humidity:.1f}%. "
            f"El Déficit de Presión de Vapor (DPV) es {latest_telemetry.vpd_kpa:.2f} kPa. "
            f"Ventilación cenital servo a {latest_telemetry.vent_servo_angle}°."
        )
    else:
        answer = (
            f"Hola, soy el asistente de la Celda Hidropónica Piloto 01 ({current_plant_profile.species_name}). "
            f"Estado {latest_jev_decision.risk_level}: Temp {latest_telemetry.air_temperature:.1f}°C, "
            f"Humedad {latest_telemetry.air_humidity:.1f}%, Estanque al {latest_telemetry.reservoir_level_percent:.1f}%. "
            f"Cada lectura se está guardando activamente en la base de datos relacional SQLite."
        )

    if api_error_notice:
        answer = f"{api_error_notice}{answer}"

    return FarmChatResponse(
        answer=answer,
        tools_consulted=tools_used + ["Motor Local Heurístico"],
        model_used="local-heuristics"
    )
