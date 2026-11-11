import os
from datetime import datetime
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
    description="Microservicio Hub para Ingesta IoT (ESP32), Orquestación JEV, Control de Actuadores y Asistente Agronómico",
    version="2.1.0"
)

# Configuración de templates HTML
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# ==============================================================================
# ESTADO EN MEMORIA (Bandeja Hidropónica Celda 01)
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

# Telemetría inicial mapeada al hardware físico real
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

# Registro de últimos comandos ejecutados
recent_commands: List[ActuatorCommand] = []


# ==============================================================================
# MOTOR DETERMINISTA DE RESPALDO (LOCAL FALLBACK - CIBERFÍSICO)
# ==============================================================================

def calculate_vpd(temp_c: float, rh_pct: float) -> float:
    """
    Calcula el Déficit de Presión de Vapor (DPV) en kPa a partir de
    la temperatura ambiente y la humedad relativa aérea.
    Fórmula de Tetens: SVP = 0.61078 * exp((17.27 * T) / (T + 237.3))
    """
    import math
    svp = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    avp = svp * (rh_pct / 100.0)
    return round(svp - avp, 2)


def evaluate_jev_local(telemetry: TelemetryInput, profile: PlantProfile) -> JevDecisionResponse:
    """
    Reglas Ciberfísicas Deterministas para la Celda Hidropónica:
    1. Regla Crítica (Nivel Estanque): Si el estanque está en <20%, BLOQUEAR la bomba para evitar cavitación.
    2. Regla Térmica (Ventilación Cenital): Si Temp > 24°C o DPV > 1.2 kPa, ABRIR compuerta servo a 90°.
    3. Regla de Recirculación: Si el nivel es óptimo, mantener la bomba lista para ciclos.
    """
    # 1. Regla de Máxima Prioridad: Protección de la Bomba contra Marcha en Seco
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

    # 2. Regla de Ventilación Cenital por Estrés Térmico o DPV Elevado
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

    # 3. Estado Óptimo y Seguro
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
    """
    Invoca al motor de decisiones TypeSafe Jev (jevai.net) vía OpenRouter / Decisions API.
    Si no hay conexión o no hay API key, conmuta al motor local sin interrupción.
    """
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
                "pump_active": telemetry.pump_active,
                "optimal_temp_range": f"{profile.optimal_temp_min_c} - {profile.optimal_temp_max_c} C",
                "optimal_humidity_range": f"{profile.optimal_humidity_min} - {profile.optimal_humidity_max} %"
            }
            questions = {
                "activate_action": {
                    "type": "noul",
                    "instructions": "¿Se requiere conmutar algún actuador físico de la bandeja (bomba, servo de ventilación o motor dosificador)?"
                },
                "dispatched_tool": {
                    "type": "choice",
                    "instructions": "¿Qué actuador debe responder?",
                    "options": ["ninguno", "bomba_agua", "servo_ventilacion", "motor_nutrientes"]
                }
            }
            payload = {
                "model": settings.JEV_MODEL_NAME,
                "state": state,
                "questions": questions
            }
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
    Sirve el Dashboard Web interactivo de la Celda Hidropónica Piloto 01.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "module": current_module,
            "plant": current_plant_profile,
            "telemetry": latest_telemetry,
            "jev": latest_jev_decision,
            "recent_commands": recent_commands[-5:],
            "now": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    )


@app.get("/api/v1/health", response_model=HealthStatus)
async def health_check():
    """
    Probe de salud para Docker / Azure Container Instances.
    """
    return HealthStatus(
        status="healthy",
        environment=settings.ENVIRONMENT,
        hardware_target="ESP32 DevKit V1 (DHT11 + BME280 + Nivel + 3 Actuadores)"
    )


@app.post("/api/v1/telemetry", response_model=Dict[str, Any])
async def ingest_telemetry(telemetry: TelemetryInput):
    """
    Ingesta de telemetría IoT desde el ESP32 o simulador.
    Evalúa automáticamente las reglas de protección y actualiza el estado.
    """
    global latest_telemetry, latest_jev_decision
    if not telemetry.vpd_kpa:
        telemetry.vpd_kpa = calculate_vpd(telemetry.air_temperature, telemetry.air_humidity)
    latest_telemetry = telemetry
    latest_jev_decision = await evaluate_jev(latest_telemetry, current_plant_profile)
    return {
        "status": "success",
        "message": "Telemetría recibida e inferencia evaluada con éxito",
        "telemetry": latest_telemetry,
        "jev_decision": latest_jev_decision
    }


@app.get("/api/v1/telemetry/latest", response_model=TelemetryInput)
async def get_latest_telemetry():
    """
    Endpoint consumido por la aplicación Android y el Dashboard para actualización en vivo.
    """
    return latest_telemetry


@app.post("/api/v1/actuators/command", response_model=Dict[str, Any])
async def send_actuator_command(cmd: ActuatorCommand):
    """
    Envía una orden manual hacia los 3 actuadores físicos:
    - bomba_agua (ON / OFF)
    - servo_ventilacion (SET_ANGLE: 0 - 180°)
    - motor_nutrientes (DISPENSE_STEPS: N pasos)
    """
    global latest_telemetry, recent_commands
    recent_commands.append(cmd)

    if cmd.target == "bomba_agua":
        latest_telemetry.pump_active = (cmd.action.upper() == "ON")
    elif cmd.target == "servo_ventilacion":
        latest_telemetry.vent_servo_angle = int(cmd.parameter_value or 0)
    elif cmd.target == "motor_nutrientes":
        latest_telemetry.stepper_dosing_steps += int(cmd.parameter_value or 0)

    return {
        "status": "command_registered",
        "actuator": cmd.target,
        "action": cmd.action,
        "parameter_value": cmd.parameter_value,
        "triggered_by": cmd.triggered_by,
        "message": f"Comando '{cmd.action}' registrado exitosamente para {cmd.target}."
    }


@app.get("/api/v1/schedule", response_model=Dict[str, Any])
async def get_schedule():
    """
    Endpoint de calendario de recirculación (Requerimiento Semana 13 Integración II).
    """
    return {
        "module_id": current_module.id,
        "crop": current_plant_profile.species_name,
        "recirculation_duration_minutes": current_plant_profile.recirculation_cycle_minutes,
        "interval_hours": current_plant_profile.recirculation_interval_hours,
        "next_cycle_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "pump_status": "ACTIVA" if latest_telemetry.pump_active else "EN_ESPERA"
    }


@app.post("/api/v1/simulate/{scenario}")
async def simulate_scenario(scenario: str):
    """
    Simulador de eventos físicos para demostración ante jueces y profesores:
    - estanque_vacio: Nivel 12%, dispara corte crítico por riesgo de cavitación.
    - calor_extremo: Temp 28.5°C, dispara apertura de ventilación servo a 90°.
    - optimo: Nivel 85%, Temp 21°C, DPV 0.95 kPa, sistema en calma.
    - recirculacion: Activa la bomba para demostración de flujo de agua.
    """
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
        raise HTTPException(
            status_code=400, 
            detail="Escenario no reconocido. Use: estanque_vacio, calor_extremo, optimo, recirculacion"
        )

    latest_jev_decision = await evaluate_jev(latest_telemetry, current_plant_profile)
    return {
        "scenario": scenario,
        "telemetry": latest_telemetry,
        "jev_decision": latest_jev_decision
    }


@app.post("/api/v1/chat/farm", response_model=FarmChatResponse)
async def chat_with_farm(request: FarmChatRequest):
    """
    Función 'Habla con tu Granja':
    Invoca al LLM (DeepSeek) inyectando en el prompt la telemetría real del ESP32,
    el perfil hidropónico y la justificación de JEV.
    """
    tools_used = ["DHT11", "BME280", "SensorNivelResistivo", "JevDecisionLog"]

    system_prompt = f"""Eres el Asistente Agronómico Inteligente de la plataforma 'AgroSense AI'.
Estás a cargo de la celda hidropónica piloto '{current_module.name}'.
Responde de forma profesional, concisa, técnica y empática basándote en los datos reales del hardware.

DATOS DE LA BANDEJA HIDROPÓNICA:
- Cultivo: {current_plant_profile.species_name} ({current_plant_profile.variety})
- Rango óptimo de Temperatura: {current_plant_profile.optimal_temp_min_c}°C a {current_plant_profile.optimal_temp_max_c}°C
- Rango óptimo de Humedad: {current_plant_profile.optimal_humidity_min}% a {current_plant_profile.optimal_humidity_max}%
- DPV óptimo: {current_plant_profile.optimal_vpd_min_kpa} a {current_plant_profile.optimal_vpd_max_kpa} kPa

MEDICIONES REALES DE SENSORES EN EL ESP32:
- Temperatura ambiental: {latest_telemetry.air_temperature} °C
- Humedad relativa aérea: {latest_telemetry.air_humidity} %
- Presión barométrica: {latest_telemetry.barometric_pressure_hpa} hPa
- Déficit de Presión de Vapor (DPV): {latest_telemetry.vpd_kpa} kPa
- Nivel de solución en estanque: {latest_telemetry.reservoir_level_percent} %

ESTADO DE ACTUADORES FÍSICOS:
- Mini-Bomba Sumergible 5V (Relé): {'ENCENDIDA (BOMBEANDO)' if latest_telemetry.pump_active else 'APAGADA (REPOSO)'}
- Servo Ventilación Cenital: {latest_telemetry.vent_servo_angle}° de apertura
- Motor Paso a Paso Nutrientes: {latest_telemetry.stepper_dosing_steps} pasos acumulados

ESTADO DEL MOTOR CIBERFÍSICO JEV:
- Nivel de riesgo: {latest_jev_decision.risk_level}
- Justificación: {latest_jev_decision.reason}
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

    # Respuesta Local Heurística Contextualizada
    q = request.question.lower()
    if "bomba" in q or "riego" in q or "agua" in q or "estanque" in q:
        answer = (
            f"El estanque reporta un nivel de solución del {latest_telemetry.reservoir_level_percent:.1f}%. "
            f"La mini-bomba sumergible de 5V se encuentra {'ENCENDIDA recirculando nutrientes' if latest_telemetry.pump_active else 'APAGADA en ciclo de reposo'}. "
            f"Evaluación de JEV: {latest_jev_decision.reason}"
        )
    elif "temperatura" in q or "humedad" in q or "clima" in q or "dpv" in q:
        answer = (
            f"En la celda registramos {latest_telemetry.air_temperature:.1f}°C de temperatura y {latest_telemetry.air_humidity:.1f}% de humedad relativa. "
            f"El Déficit de Presión de Vapor (DPV) calculado es de {latest_telemetry.vpd_kpa:.2f} kPa (Rango ideal: 0.8 a 1.2 kPa). "
            f"El servomotor de ventilación cenital se encuentra a {latest_telemetry.vent_servo_angle}°."
        )
    else:
        answer = (
            f"Hola, soy el asistente de la Celda Hidropónica Piloto 01 ({current_plant_profile.species_name}). "
            f"Actualmente el sistema está en estado {latest_jev_decision.risk_level}: Temp {latest_telemetry.air_temperature:.1f}°C, "
            f"Humedad {latest_telemetry.air_humidity:.1f}%, Presión {latest_telemetry.barometric_pressure_hpa:.1f} hPa y Estanque al {latest_telemetry.reservoir_level_percent:.1f}%. "
            f"¿Deseas información sobre el estado de la bomba, ventilación o nutrientes?"
        )

    if api_error_notice:
        answer = f"{api_error_notice}{answer}"

    return FarmChatResponse(
        answer=answer,
        tools_consulted=tools_used + ["Motor Local Heurístico"],
        model_used="local-heuristics"
    )
