from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==============================================================================
# 1. PERFIL BOTÁNICO DE LA BANDEJA CELULAR (HIDROPONÍA PILOTO 01)
# ==============================================================================

class PlantProfile(BaseModel):
    """
    Ficha agronómica de la especie cultivada en la bandeja hidropónica.
    Define los umbrales microclimáticos y el ciclo de recirculación.
    """
    id: str = Field(default="crop_frutilla_hidroponica", description="Identificador único del cultivo")
    species_name: str = Field(default="Frutilla Hidropónica (Fragaria x ananassa)", description="Nombre de la especie")
    variety: Optional[str] = Field("Albion / San Andreas", description="Variedad hidropónica")
    optimal_temp_min_c: float = Field(18.0, description="Temperatura ambiental mínima óptima (°C)")
    optimal_temp_max_c: float = Field(24.0, description="Temperatura ambiental máxima óptima (°C)")
    optimal_humidity_min: float = Field(55.0, description="Humedad relativa mínima (%)")
    optimal_humidity_max: float = Field(75.0, description="Humedad relativa máxima (%)")
    optimal_vpd_min_kpa: float = Field(0.8, description="Déficit de Presión de Vapor mínimo (kPa)")
    optimal_vpd_max_kpa: float = Field(1.2, description="Déficit de Presión de Vapor máximo (kPa)")
    recirculation_cycle_minutes: int = Field(15, description="Minutos de bomba encendida por ciclo")
    recirculation_interval_hours: int = Field(2, description="Horas entre ciclos de recirculación")
    researched_by_llm: bool = Field(True, description="Si los parámetros fueron calibrados con IA")


class HydroponicModule(BaseModel):
    """
    Entidad Celda Piloto: Prototipo celular de 1 bandeja hidropónica.
    """
    id: str = Field("celda-01", description="ID único del módulo (ej: celda-01)")
    name: str = Field("Bandeja Hidropónica Piloto - Frutilla", description="Nombre descriptivo")
    location: str = Field("Santo Tomás Temuco - Laboratorio IoT", description="Ubicación física")
    plant_profile_id: str = Field("crop_frutilla_hidroponica", description="Cultivo asignado")
    growth_stage: str = Field("FLORACION", description="Etapa fenológica: VEGETATIVO, FLORACION, COSECHA")
    active: bool = Field(True, description="Estado operativo de la celda")


# ==============================================================================
# 2. INGESTA DE TELEMETRÍA (SENSORES REALES DEL MVP DE HARDWARE)
# ==============================================================================

class TelemetryInput(BaseModel):
    """
    Mediciones en tiempo real emitidas por el ESP32 DevKit V1 vía MQTT o REST.
    Mapeadas exactamente al inventario físico de hardware.
    """
    module_id: str = Field(default="celda-01", description="ID de la bandeja")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Marca temporal UTC")

    # --- Sensores Físicos Reales Conectados ---
    air_temperature: float = Field(..., ge=-10.0, le=60.0, description="Temperatura ambiental °C (DHT11 / BME280)")
    air_humidity: float = Field(..., ge=0.0, le=100.0, description="Humedad relativa % (DHT11)")
    barometric_pressure_hpa: float = Field(default=1013.25, ge=800.0, le=1200.0, description="Presión atmosférica hPa (BME280 / BMP280 en I2C)")
    reservoir_level_percent: float = Field(..., ge=0.0, le=100.0, description="Nivel de estanque % (Sensor Resistivo GPIO 34 con pulso en 25)")

    # --- Métrica Fisiológica Calculada ---
    vpd_kpa: Optional[float] = Field(None, description="Déficit de Presión de Vapor calculado (kPa)")

    # --- Estado de Actuadores Físicos en la Maqueta ---
    pump_active: bool = Field(default=False, description="Estado de la mini-bomba sumergible 5V (Relé GPIO 26)")
    vent_servo_angle: int = Field(default=0, ge=0, le=180, description="Ángulo del servo SG90 para ventilación (GPIO 18)")
    stepper_dosing_steps: int = Field(default=0, description="Pasos acumulados del motor PaP 28BYJ-48 (ULN2003)")

    # --- Sensores de Fase 2 (Extensiones Futuras - Nullable) ---
    ph_level: Optional[float] = Field(None, ge=0.0, le=14.0, description="Sonda de pH análoga (Fase 2)")
    ec_salinity_dsm: Optional[float] = Field(None, ge=0.0, le=10.0, description="Sonda de conductividad EC (Fase 2)")
    light_lux: Optional[float] = Field(None, ge=0.0, le=100000.0, description="Sensor fotocelda LDR (Fase 2)")


# ==============================================================================
# 3. CONTROL DE ACTUADORES FÍSICOS (POLIMÓRFICO / SOA)
# ==============================================================================

class ActuatorCommand(BaseModel):
    """
    Comando emitido desde el Dashboard Web, App Android o Motor de Reglas
    hacia los actuadores físicos del ESP32.
    """
    module_id: str = Field(default="celda-01")
    target: str = Field(..., description="bomba_agua | servo_ventilacion | motor_nutrientes")
    action: str = Field(..., description="ON | OFF | SET_ANGLE | DISPENSE_STEPS")
    parameter_value: Optional[float] = Field(default=0.0, description="Duración en seg, ángulo (0-180°) o pasos motor")
    triggered_by: str = Field(default="manual", description="manual_android | manual_web | jev_rule | schedule")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# 4. INFERENCIA CIBERFÍSICA (TYPESAFE JEV - jevai.net)
# ==============================================================================

class JevDecisionResponse(BaseModel):
    """
    Salida de decisión del Motor JEV (jevai.net):
    - Decisión ciberfísica en <80ms.
    - Protección contra cavitación de bomba y sobrecalentamiento.
    """
    action_required: bool = Field(..., description="¿Se requiere intervención de actuadores?")
    recommended_pump_state: bool = Field(..., description="Estado recomendado para la bomba sumergible")
    recommended_vent_angle: int = Field(0, description="Ángulo recomendado para ventilación cenital (0-180°)")
    reason: str = Field(..., description="Explicación determinista de la regla")
    risk_level: str = Field(default="NORMAL", description="NORMAL | WARNING | CRITICAL")
    execution_time_ms: float = Field(default=80.0, description="Latencia de inferencia en milisegundos")
    fallback_rule_applied: bool = Field(False, description="Indica si operó en modo local sin internet")
    executed_at: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# 5. ASISTENTE AGRONÓMICO CONVERSACIONAL (DEEPSEEK LLM)
# ==============================================================================

class FarmChatRequest(BaseModel):
    """
    Petición para el asistente inteligente en lenguaje natural.
    """
    question: str = Field(..., description="Consulta del usuario (ej: ¿Por qué la humedad está baja?)")
    session_id: Optional[str] = Field("session_01", description="ID de sesión")
    include_live_telemetry: bool = Field(True, description="Adjuntar los últimos sensores al prompt del LLM")


class FarmChatResponse(BaseModel):
    """
    Respuesta agronómica generada por DeepSeek LLM con contexto de la celda.
    """
    answer: str = Field(..., description="Explicación agronómica fundamentada")
    tools_consulted: List[str] = Field(default_factory=list, description="Variables analizadas (DHT11, BME, etc.)")
    model_used: str = Field(default="deepseek-chat", description="Modelo LLM de inferencia")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# 6. ESTADO DE SALUD DEL SERVICIO (AZURE / DOCKER PROBE)
# ==============================================================================

class HealthStatus(BaseModel):
    """
    Chequeo de disponibilidad del backend.
    """
    status: str = "healthy"
    service: str = "AgroSense AI (ASAI) - Core Backend Hub"
    version: str = "2.1.0"
    environment: str = "production"
    hardware_target: str = "ESP32 DevKit V1 (DHT11 + BME280 + Nivel + 3 Actuadores)"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
