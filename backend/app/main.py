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
    Sector,
    TelemetryInput,
    JevDecisionResponse,
    FarmChatRequest,
    FarmChatResponse,
    HealthStatus
)

app = FastAPI(
    title="AgroSense AI — Cloud Management Hub",
    description="Microservicio Cloud para Ingesta de Telemetría IoT, Orquestación JEV y Asistente Agronómico",
    version="1.0.0"
)

# Configuración de templates HTML
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# ==============================================================================
# ESTADO EN MEMORIA (Base de datos en memoria para el prototipo Cloud)
# ==============================================================================
current_plant_profile = PlantProfile(
    id="crop_avellano_tonda",
    common_name="Avellano Europeo",
    scientific_name="Corylus avellana",
    variety="Tonda di Giffoni",
    optimal_moisture_min=50.0,
    optimal_moisture_max=70.0,
    optimal_ph_min=5.8,
    optimal_ph_max=6.8,
    frost_critical_temp=-1.5,
    max_wind_tolerance_kmh=20.0,
    ideal_npk_ratio="12-8-16",
    common_diseases=["Botrytis", "Pulgón del avellano", "Tizón bacteriano"],
    researched_by_llm=True,
    research_notes="Cultivo de alto valor en La Araucanía. Sensible a encharcamientos prolongados y heladas tardías."
)

current_sector = Sector(
    id="cuartel_01_avellanos",
    name="Cuartel 1 - Avellanos Norte",
    soil_type="Trumao / Volcánico",
    area_hectares=4.5,
    plant_profile_id=current_plant_profile.id,
    growth_stage="FLORACION"
)

# Lectura inicial de telemetría
latest_telemetry = TelemetryInput(
    device_id="esp32_nodo_01",
    sector_id=current_sector.id,
    soil_moisture=42.0,
    ambient_temperature=16.5,
    soil_temperature=13.0,
    ambient_humidity=58.0,
    ph_level=6.2,
    nitrogen_ppm=15.0,
    phosphorus_ppm=9.0,
    potassium_ppm=18.0,
    wind_speed_kmh=8.0
)

# ==============================================================================
# MOTOR DE INFERENCIA IA: TYPESAFE JEV (jevai.net) & FALLBACK LOCAL
# ==============================================================================

def evaluate_jev_local(telemetry: TelemetryInput, profile: PlantProfile) -> JevDecisionResponse:
    """
    Motor Heurístico Local de Respaldo (Fallback sin conexión):
    Calcula deterministamente las 3 variables de control si la API de Jev no está disponible.
    """
    # 1. Regla de Máxima Prioridad: Protección de Heladas
    if telemetry.ambient_temperature <= profile.frost_critical_temp:
        return JevDecisionResponse(
            decision_action=False,
            decision_intensity=0,
            commanded_tools=["calefactor_antihelada_sec1"],
            justification_reason=f"BLOQUEO POR HELADA (Modo Local): Temp ambiente ({telemetry.ambient_temperature}°C) <= umbral crítico ({profile.frost_critical_temp}°C). Riego cancelado para evitar congelación foliar y radicular.",
            lease_duration_seconds=1800,
            failsafe_active=True
        )

    # 2. Regla de Seguridad: Viento Excesivo para Equipos
    if telemetry.wind_speed_kmh and telemetry.wind_speed_kmh > profile.max_wind_tolerance_kmh:
        return JevDecisionResponse(
            decision_action=False,
            decision_intensity=0,
            commanded_tools=["alerta_viento_alto"],
            justification_reason=f"SUSPENSIÓN POR VIENTO (Modo Local): Ráfagas de {telemetry.wind_speed_kmh} km/h superan el límite de {profile.max_wind_tolerance_kmh} km/h. Drones y aspersores detenidos.",
            lease_duration_seconds=900,
            failsafe_active=False
        )

    # 3. Regla de Riego: Humedad deficiente
    if telemetry.soil_moisture < profile.optimal_moisture_min:
        deficit = profile.optimal_moisture_min - telemetry.soil_moisture
        power = min(95, int(60 + (deficit * 2.5)))
        return JevDecisionResponse(
            decision_action=True,
            decision_intensity=power,
            commanded_tools=["bomba_riego_principal", "electrovalvula_cuartel_01"],
            justification_reason=f"RIEGO ACTIVADO (Modo Local): Humedad de suelo ({telemetry.soil_moisture}%) inferior al umbral mínimo del cultivo ({profile.optimal_moisture_min}%). Déficit hídrico de {deficit:.1f}%.",
            lease_duration_seconds=1200,
            failsafe_active=False
        )

    # 4. Regla: Suelo Óptimo o Saturado
    return JevDecisionResponse(
        decision_action=False,
        decision_intensity=0,
        commanded_tools=[],
        justification_reason=f"CONDICIÓN ÓPTIMA (Modo Local): Humedad ({telemetry.soil_moisture}%) dentro del rango ideal ({profile.optimal_moisture_min}% - {profile.optimal_moisture_max}%). Riego en reposo para cuidar el agua.",
        lease_duration_seconds=1800,
        failsafe_active=False
    )

async def evaluate_jev(telemetry: TelemetryInput, profile: PlantProfile) -> JevDecisionResponse:
    """
    Invoca a la IA de Toma de Decisiones TypeSafe Jev (jevai.net) vía OpenRouter Decisions API.
    Envía el estado de la granja (telemetría + perfil de cultivo) y formula las 3 preguntas nativas:
    1. Noul: "¿Se debe activar la maquinaria?" -> Booleano 'Sí o No'
    2. Score: "¿Cuál es el nivel de modulación requerido (0-100%)?" -> Intensidad '0 - 100'
    3. Choice: "¿Qué actuador o herramienta específica debe despacharse?" -> 'Herramientas de la lista'
    
    Si no hay API key o hay fallo de red, conmuta transparentemente al motor de reglas local.
    """
    api_key = settings.LLM_API_KEY.strip()
    if api_key and api_key != "tu_api_key_aqui" and not api_key.startswith("dev_local_key"):
        try:
            url = settings.JEV_DECISIONS_API_URL
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agrosense.ai",
                "X-Title": "AgroSense AI - TypeSafe Jev Decisions"
            }
            state = {
                "sector": current_sector.name,
                "crop": f"{profile.common_name} ({profile.variety})",
                "soil_moisture_pct": telemetry.soil_moisture,
                "optimal_moisture_min": profile.optimal_moisture_min,
                "optimal_moisture_max": profile.optimal_moisture_max,
                "ambient_temperature_c": telemetry.ambient_temperature,
                "frost_critical_temp_c": profile.frost_critical_temp,
                "wind_speed_kmh": telemetry.wind_speed_kmh or 0.0,
                "max_wind_tolerance_kmh": profile.max_wind_tolerance_kmh,
                "ph_level": telemetry.ph_level or 6.5
            }
            questions = {
                "activate_action": {
                    "type": "noul",
                    "instructions": "¿Se debe activar alguna acción de riego o protección física inmediata para el cultivo?"
                },
                "modulation_intensity": {
                    "type": "score",
                    "instructions": "Nivel de potencia o modulación de intensidad requerida de 0 a 100 por ciento.",
                    "levels": ["0", "20", "40", "60", "80", "100"]
                },
                "dispatched_tool": {
                    "type": "choice",
                    "instructions": "¿Cuál de las herramientas registradas en la flota debe entrar en operación?",
                    "options": [
                        "ninguna",
                        "bomba_riego_principal",
                        "calefactor_antihelada_sec1",
                        "electrovalvula_cuartel_01",
                        "dron_fumigador_alfa"
                    ]
                }
            }
            payload = {
                "model": settings.JEV_MODEL_NAME,
                "state": state,
                "questions": questions
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    decisions = data.get("decisions", {})
                    
                    # 1. Noul: Sí o No
                    noul_obj = decisions.get("activate_action", {})
                    if "value" in noul_obj and isinstance(noul_obj["value"], bool):
                        is_active = noul_obj["value"]
                    else:
                        is_active = float(noul_obj.get("score", noul_obj.get("probability", 0))) > 0.5
                    
                    # 2. Score: 0 a 100
                    score_obj = decisions.get("modulation_intensity", {})
                    score_val = score_obj.get("value", "0")
                    try:
                        intensity = int(score_val)
                    except Exception:
                        intensity = int(float(score_obj.get("score", 0)) * 100) if is_active else 0
                    
                    # 3. Choice: Herramientas de la lista
                    choice_val = decisions.get("dispatched_tool", {}).get("value", "ninguna")
                    tools = [choice_val] if choice_val and choice_val != "ninguna" else []
                    
                    return JevDecisionResponse(
                        decision_action=is_active,
                        decision_intensity=intensity if is_active else 0,
                        commanded_tools=tools,
                        justification_reason=f"Decisión IA emitida por TypeSafe Jev ({settings.JEV_MODEL_NAME}): Noul={is_active}, Score={intensity}%, Choice={choice_val}",
                        lease_duration_seconds=1200,
                        failsafe_active=False
                    )
        except Exception:
            # En caso de error de red, pasa transparentemente al motor local
            pass

    return evaluate_jev_local(telemetry, profile)

# Decisión inicial (usando motor local en el arranque para no bloquear)
latest_jev_decision = evaluate_jev_local(latest_telemetry, current_plant_profile)


# ==============================================================================
# ENDPOINTS REST DE LA API
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Sirve el Dashboard Web interactivo de AgroSense AI para Azure.
    """
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sector": current_sector,
            "plant": current_plant_profile,
            "telemetry": latest_telemetry,
            "jev": latest_jev_decision,
            "now": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    )

@app.get("/api/v1/health", response_model=HealthStatus)
async def health_check():
    """
    Probe de salud para Azure Container Instances (ACI).
    """
    return HealthStatus(
        environment=settings.ENVIRONMENT
    )

@app.post("/api/v1/telemetry", response_model=Dict[str, Any])
async def ingest_telemetry(telemetry: TelemetryInput):
    """
    Ingesta de telemetría IoT desde ESP32 u orígenes externos.
    Dispara automáticamente la inferencia de JEV.
    """
    global latest_telemetry, latest_jev_decision
    latest_telemetry = telemetry
    latest_jev_decision = await evaluate_jev(latest_telemetry, current_plant_profile)
    return {
        "status": "success",
        "message": "Telemetría recibida y evaluada por JEV",
        "telemetry": latest_telemetry,
        "jev_decision": latest_jev_decision
    }

@app.get("/api/v1/jev/decision", response_model=JevDecisionResponse)
async def get_jev_decision():
    """
    Consulta la última decisión tomada por el motor JEV.
    """
    return latest_jev_decision

@app.post("/api/v1/simulate/{scenario}")
async def simulate_scenario(scenario: str):
    """
    Simulador de escenarios para pruebas y demostración ante jueces y profesores:
    - sequia: Humedad baja (22%), dispara riego potente.
    - helada: Temperatura bajo cero (-2.5°C), activa protocolo anti-helada.
    - optimo: Humedad ideal (62%), temp templada (19°C), reposo hídrico.
    - viento: Viento de 28 km/h, suspende maquinaria.
    """
    global latest_telemetry, latest_jev_decision

    if scenario == "sequia":
        latest_telemetry.soil_moisture = 22.0
        latest_telemetry.ambient_temperature = 24.0
        latest_telemetry.wind_speed_kmh = 6.0
    elif scenario == "helada":
        latest_telemetry.ambient_temperature = -2.5
        latest_telemetry.soil_moisture = 48.0
        latest_telemetry.wind_speed_kmh = 4.0
    elif scenario == "optimo":
        latest_telemetry.soil_moisture = 62.0
        latest_telemetry.ambient_temperature = 19.5
        latest_telemetry.wind_speed_kmh = 9.0
    elif scenario == "viento":
        latest_telemetry.wind_speed_kmh = 28.5
        latest_telemetry.ambient_temperature = 17.0
    else:
        raise HTTPException(status_code=400, detail="Escenario no reconocido. Use: sequia, helada, optimo, viento")

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
    Invoca al LLM (DeepSeek / OpenAI compatible) inyectando en el System Prompt
    la telemetría real del campo, el perfil botánico investigado y la justificación de JEV.
    Si no hay API key configurada o falla la red, conmuta a modo local sin caerse.
    """
    tools_used = ["TelemetryReading", "PlantProfile", "JevDecisionLog"]

    # Preparar el contexto agronómico completo para DeepSeek / LLM
    system_prompt = f"""Eres el Asistente Agronómico Inteligente de la plataforma 'AgroSense AI'.
Tu labor es responder a las consultas del agricultor con tono profesional, empático, claro y fundamentado en los datos reales del campo.

CONTEXTO AGRONÓMICO DEL SECTOR:
- Cuartel: {current_sector.name} ({current_sector.soil_type}, {current_sector.area_hectares} ha)
- Especie: {current_plant_profile.common_name} (Variedad: {current_plant_profile.variety})
- Etapa fenológica: {current_sector.growth_stage}
- Requisitos botánicos ideales:
  * Humedad de suelo óptima: {current_plant_profile.optimal_moisture_min}% a {current_plant_profile.optimal_moisture_max}%
  * pH de suelo óptimo: {current_plant_profile.optimal_ph_min} a {current_plant_profile.optimal_ph_max}
  * Umbral crítico de helada: {current_plant_profile.frost_critical_temp} °C
  * Límite de viento: {current_plant_profile.max_wind_tolerance_kmh} km/h
  * Proporción NPK recomendada: {current_plant_profile.ideal_npk_ratio}
  * Plagas/hongos comunes: {', '.join(current_plant_profile.common_diseases)}
  * Notas agronómicas: {current_plant_profile.research_notes}

MEDICIONES ACTUALES DE SENSORES EN TERRENO:
- Humedad de suelo: {latest_telemetry.soil_moisture}%
- Temperatura ambiente: {latest_telemetry.ambient_temperature} °C
- Temperatura de raíz: {latest_telemetry.soil_temperature} °C
- Humedad ambiental: {latest_telemetry.ambient_humidity}%
- Nivel de pH: {latest_telemetry.ph_level}
- Nutrientes NPK: Nitrógeno {latest_telemetry.nitrogen_ppm} ppm, Fósforo {latest_telemetry.phosphorus_ppm} ppm, Potasio {latest_telemetry.potassium_ppm} ppm
- Viento: {latest_telemetry.wind_speed_kmh} km/h

ESTADO DEL MOTOR DE CONTROL EN TIEMPO REAL (JEV):
- Estado de activación: {'ACTIVO' if latest_jev_decision.decision_action else 'EN REPOSO'}
- Modulación de potencia: {latest_jev_decision.decision_intensity}%
- Herramientas en marcha: {', '.join(latest_jev_decision.commanded_tools) if latest_jev_decision.commanded_tools else 'Ninguna'}
- Justificación determinista de JEV: {latest_jev_decision.justification_reason}

INSTRUCCIONES:
1. Responde directamente a la consulta del usuario.
2. Explica el por qué de las decisiones del sistema basándote en los números medidos.
3. Sé conciso y utiliza recomendaciones agronómicas aplicables al trabajo de campo."""

    # 1. Intentar invocar a la API de DeepSeek / OpenAI si hay Key real configurada
    api_key = settings.LLM_API_KEY.strip()
    if api_key and api_key != "tu_api_key_aqui" and not api_key.startswith("dev_local_key"):
        try:
            url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://agrosense.ai",
                "X-Title": "AgroSense AI Cloud Hub"
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
            async with httpx.AsyncClient(timeout=25.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    ai_answer = data["choices"][0]["message"]["content"]
                    return FarmChatResponse(
                        answer=ai_answer,
                        tools_consulted=tools_used + [f"DeepSeek ({settings.LLM_MODEL_NAME})"]
                    )
        except Exception:
            # Si hay timeout o error de red, pasa al fallback local transparente
            pass

    # 2. Modo Fallback Local (Respuestas contextualizadas sin depender de saldo/red)
    q = request.question.lower()

    if "riego" in q or "regar" in q or "bomba" in q:
        if latest_jev_decision.decision_action:
            answer = (
                f"En este momento el riego está ACTIVO al {latest_jev_decision.decision_intensity}% de potencia "
                f"en el sector '{current_sector.name}'. Motivo de JEV: {latest_jev_decision.justification_reason} "
                f"La humedad actual del suelo es de {latest_telemetry.soil_moisture}% frente al mínimo óptimo de {current_plant_profile.optimal_moisture_min}%."
            )
        else:
            answer = (
                f"Actualmente el riego se encuentra DETENIDO. Motivo evaluado por JEV: {latest_jev_decision.justification_reason} "
                f"La humedad de suelo está en {latest_telemetry.soil_moisture}%, lo cual cuida los recursos de la granja."
            )
    elif "helada" in q or "temperatura" in q or "frío" in q:
        answer = (
            f"La temperatura ambiental registrada es de {latest_telemetry.ambient_temperature}°C. "
            f"El umbral crítico de helada para tus {current_plant_profile.common_name} es de {current_plant_profile.frost_critical_temp}°C. "
            f"Estado del sistema: {'ALERTA DE HELADA ACTIVA' if latest_telemetry.ambient_temperature <= current_plant_profile.frost_critical_temp else 'Temperatura en rango seguro'}."
        )
    elif "planta" in q or "cultivo" in q or "avellano" in q:
        answer = (
            f"El cuartel activo tiene cultivado '{current_plant_profile.common_name}' (Variedad: {current_plant_profile.variety}). "
            f"Parámetros investigados: Humedad óptima entre {current_plant_profile.optimal_moisture_min}% y {current_plant_profile.optimal_moisture_max}%, "
            f"pH entre {current_plant_profile.optimal_ph_min} y {current_plant_profile.optimal_ph_max}. "
            f"Consejo agronómico: {current_plant_profile.research_notes}"
        )
    elif "nutriente" in q or "ph" in q or "npk" in q:
        answer = (
            f"El pH de tu suelo está en {latest_telemetry.ph_level} (Rango ideal: {current_plant_profile.optimal_ph_min} - {current_plant_profile.optimal_ph_max}). "
            f"Nivel de macronutrientes: Nitrógeno: {latest_telemetry.nitrogen_ppm} ppm, Fósforo: {latest_telemetry.phosphorus_ppm} ppm, "
            f"Potasio: {latest_telemetry.potassium_ppm} ppm. Proporción NPK sugerida: {current_plant_profile.ideal_npk_ratio}."
        )
    else:
        answer = (
            f"Hola, soy el asistente botánico de AgroSense AI. Tu granja en '{current_sector.name}' "
            f"reporta humedad de {latest_telemetry.soil_moisture}%, temperatura de {latest_telemetry.ambient_temperature}°C "
            f"y viento de {latest_telemetry.wind_speed_kmh} km/h. Decisión de JEV: '{latest_jev_decision.justification_reason}'. "
            f"¿Deseas consultar sobre riego, fertilización o riesgo de heladas?"
        )

    return FarmChatResponse(
        answer=answer,
        tools_consulted=tools_used + ["Motor Local Heurístico"]
    )
