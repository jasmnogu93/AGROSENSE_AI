from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ==============================================================================
# 1. PERFIL BOTÁNICO Y SECTORES DE LA GRANJA
# ==============================================================================

class PlantProfile(BaseModel):
    """
    Entidad PlantProfile: Ficha agronómica investigada por el LLM.
    Define los umbrales fisiológicos de calibración para JEV.
    """
    id: str = Field(..., description="Identificador único del cultivo (ej: crop_avellano_tonda)")
    common_name: str = Field(..., description="Nombre común (ej: Avellano Europeo)")
    scientific_name: Optional[str] = Field(None, description="Nombre científico botánico")
    variety: Optional[str] = Field(None, description="Variedad o clon")
    optimal_moisture_min: float = Field(..., description="Humedad mínima óptima (%)")
    optimal_moisture_max: float = Field(..., description="Humedad máxima óptima (%)")
    optimal_ph_min: float = Field(..., description="pH mínimo tolerado")
    optimal_ph_max: float = Field(..., description="pH máximo tolerado")
    frost_critical_temp: float = Field(..., description="Temperatura umbral de helada (°C)")
    max_wind_tolerance_kmh: float = Field(20.0, description="Viento máximo tolerado (km/h)")
    ideal_npk_ratio: Optional[str] = Field("12-8-16", description="Proporción N-P-K ideal")
    common_diseases: List[str] = Field(default_factory=list, description="Plagas y hongos típicos")
    researched_by_llm: bool = Field(True, description="Si fue investigado por IA")
    research_notes: Optional[str] = Field(None, description="Notas agronómicas de manejo")


class Sector(BaseModel):
    """
    Entidad Sector: Cuartel físico de la granja.
    """
    id: str = Field(..., description="Código del cuartel (ej: cuartel_01_avellanos)")
    name: str = Field(..., description="Nombre visible del sector")
    soil_type: str = Field("Trumao / Volcánico", description="Tipo de suelo")
    area_hectares: float = Field(..., description="Superficie en hectáreas")
    plant_profile_id: str = Field(..., description="FK al cultivo actual")
    growth_stage: str = Field("FLORACION", description="Etapa fenológica")


# ==============================================================================
# 2. INGESTA DE TELEMETRÍA (SUELO ESTRATIFICADO + AMBIENTE COMPLETO)
# ==============================================================================

class TelemetryInput(BaseModel):
    """
    Entidad TelemetryReading: Mediciones en tiempo real recibidas desde ESP32 / Sensores.
    Incluye estratificación de suelo y variables microclimáticas profesionales.
    """
    device_id: str = Field("esp32_nodo_01", description="ID del dispositivo en terreno")
    sector_id: str = Field("cuartel_01_avellanos", description="ID del sector")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Marca temporal UTC")

    # --- Humedad y Suelo Principal ---
    soil_moisture: float = Field(..., ge=0, le=100, description="Humedad suelo promedio / superficial (%)")
    soil_temperature: Optional[float] = Field(15.0, description="Temperatura radicular (°C)")
    ph_level: Optional[float] = Field(6.2, ge=0, le=14, description="Acidez del suelo (0 - 14)")

    # --- Estratificación de Humedad Multiprofundidad ---
    soil_moisture_20cm: Optional[float] = Field(None, ge=0, le=100, description="Humedad a 20 cm (raíz activa)")
    soil_moisture_40cm: Optional[float] = Field(None, ge=0, le=100, description="Humedad a 40 cm (zona de reserva)")
    soil_moisture_60cm: Optional[float] = Field(None, ge=0, le=100, description="Humedad a 60 cm (control de percolación)")
    matric_potential_kpa: Optional[float] = Field(None, description="Tensión de agua en suelo (kPa / cbar)")
    ec_salinity_dsm: Optional[float] = Field(None, description="Conductividad eléctrica / Salinidad (dS/m)")

    # --- Nutrición Mineral (Primarios NPK y Secundarios Ca/Mg) ---
    nitrogen_ppm: Optional[float] = Field(14.0, description="Nitrógeno N (ppm)")
    phosphorus_ppm: Optional[float] = Field(8.0, description="Fósforo P (ppm)")
    potassium_ppm: Optional[float] = Field(18.0, description="Potasio K (ppm)")
    calcium_ppm: Optional[float] = Field(None, description="Calcio Ca (ppm)")
    magnesium_ppm: Optional[float] = Field(None, description="Magnesio Mg (ppm)")

    # --- Microclima Atmosférico y Estación Meteorológica ---
    ambient_temperature: float = Field(..., description="Temperatura ambiental (°C)")
    ambient_humidity: Optional[float] = Field(58.0, ge=0, le=100, description="Humedad ambiental (%)")
    wind_speed_kmh: Optional[float] = Field(8.0, description="Velocidad del viento (km/h)")
    wind_direction_deg: Optional[float] = Field(None, ge=0, le=360, description="Dirección del viento en grados (0-360°)")
    rain_gauge_mm: Optional[float] = Field(0.0, ge=0, description="Lluvia acumulada 24h (mm)")
    leaf_wetness_minutes: Optional[float] = Field(0.0, description="Mojamiento foliar acumulado (min)")
    vpd_kpa: Optional[float] = Field(None, description="Déficit de Presión de Vapor - VPD (kPa)")
    dew_point_c: Optional[float] = Field(None, description="Punto de rocío (°C)")
    par_radiation: Optional[float] = Field(None, description="Radiación fotosintética útil PAR (μmol/m²/s)")


# ==============================================================================
# 3. ENTIDADES DE CICLO COMPLETO DE CULTIVO (PREPARACIÓN, FENOLOGÍA, SANIDAD, COSECHA)
# ==============================================================================

class ManagementZone(BaseModel):
    """
    Zonificación de Suelo y Preparación de Terreno / Arado.
    Permite labranza de precisión y subsolado según compactación.
    """
    id: str = Field(..., description="ID de la zona (ej: zm_cuartel1_alta_arcilla)")
    sector_id: str = Field(..., description="ID del sector al que pertenece")
    texture_class: str = Field("Franco Arcilloso", description="Clase textural del suelo")
    organic_matter_percent: float = Field(4.5, description="Porcentaje de materia orgánica (%)")
    compaction_psi: float = Field(220.0, description="Resistencia a la penetración (psi)")
    plowing_depth_recommended_cm: int = Field(35, description="Profundidad recomendada de subsolado (cm)")
    requires_subsoiling: bool = Field(False, description="¿Requiere romper pie de arado?")


class CropPhenology(BaseModel):
    """
    Seguimiento del Desarrollo Fenológico y Demanda Hídrica (FAO 56).
    """
    id: str = Field(..., description="ID del registro fenológico")
    sector_id: str = Field(..., description="Sector monitoreado")
    current_stage: str = Field("FLORACION", description="Etapa fenológica actual")
    gdd_accumulated: float = Field(420.5, description="Grados-Día de Crecimiento acumulados")
    chill_hours_accumulated: float = Field(680.0, description="Horas de frío acumuladas (< 7.2°C)")
    kc_coefficient: float = Field(0.85, description="Coeficiente de cultivo dinámico (Kc)")
    etc_mm_day: float = Field(3.8, description="Evapotranspiración del cultivo estimada (mm/día)")


class PhytosanitaryApplication(BaseModel):
    """
    Registro Fitosanitario y Control de Días de Carencia (GlobalGAP).
    """
    id: str = Field(..., description="ID de la aplicación (ej: app_2026_01)")
    sector_id: str = Field(..., description="Sector tratado")
    target_pest_or_disease: str = Field(..., description="Plaga u hongo objetivo (ej: Botrytis cinerea)")
    product_name: str = Field(..., description="Nombre comercial del producto")
    active_ingredient: str = Field(..., description="Ingrediente químico o biológico activo")
    dose_per_hectare: str = Field(..., description="Dosis aplicada (ej: 1.5 L/ha)")
    application_date: datetime = Field(default_factory=datetime.utcnow, description="Fecha y hora de aplicación")
    phi_days: int = Field(..., description="Días de Carencia (Pre-Harvest Interval)")
    safe_harvest_date: date = Field(..., description="Fecha mínima legal para iniciar cosecha")
    applied_by: str = Field("dron_fumigador_01", description="Operador humano o dron de la flota")


class HarvestQualityLog(BaseModel):
    """
    Monitoreo de Calidad Pre-Cosecha y Madurez de Fruta.
    """
    id: str = Field(..., description="ID de la muestra de calidad")
    sector_id: str = Field(..., description="Sector evaluado")
    sampling_date: datetime = Field(default_factory=datetime.utcnow, description="Fecha de muestreo")
    brix_degrees: float = Field(..., description="Concentración de azúcares solubles (°Brix)")
    firmness_durofel: float = Field(..., description="Firmeza de pulpa (Unidades Durofel o kg/cm²)")
    titratable_acidity: Optional[float] = Field(None, description="Acidez titulable (% ácido málico/cítrico)")
    harvest_ready: bool = Field(False, description="¿Cumple estándares comerciales de cosecha?")


class WorkOrder(BaseModel):
    """
    Órdenes de Trabajo del Campo (Despacho a humanos o robots autónomos).
    """
    id: str = Field(..., description="ID de la orden (ej: wo_riego_20260401)")
    sector_id: str = Field(..., description="Sector objetivo")
    operation_type: str = Field(..., description="ARADO, RIEGO, FERTIRRIEGO, PULVERIZACION, PODA, COSECHA")
    assigned_entity_type: str = Field("AUTONOMOUS_ACTUATOR", description="HUMANO o AUTONOMOUS_ACTUATOR / ROBOT")
    assigned_entity_id: str = Field("bomba_riego_principal", description="ID de maquinaria o cuadrilla")
    status: str = Field("COMPLETED", description="PENDING, IN_PROGRESS, COMPLETED, CANCELLED")
    weather_safe_validated: bool = Field(True, description="¿Fue validada la ventana climática por IA?")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ==============================================================================
# 4. MOTOR DE DECISIONES TYPESAFE JEV (jevai.net)
# ==============================================================================

class JevDecisionResponse(BaseModel):
    """
    Salida de decisión del Motor JEV (jevai.net):
    1. Noul: Booleano con probabilidad (true/false)
    2. Score: Modulación continua (0 - 100%)
    3. Choice: Selección de actuadores/herramientas del catálogo
    """
    decision_action: bool = Field(..., description="¿Se activa maniobra física? (true/false)")
    decision_intensity: int = Field(..., ge=0, le=100, description="Intensidad ordenada (0 - 100%)")
    commanded_tools: List[str] = Field(..., description="Herramientas comandadas de la flota")
    justification_reason: str = Field(..., description="Fundamentación determinista de la regla")
    lease_duration_seconds: int = Field(900, description="Tiempo de vigencia seguro (segundos)")
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de inferencia")
    failsafe_active: bool = Field(False, description="Si opera en modo de prevención")


# ==============================================================================
# 5. ASISTENTE COGNITIVO ("HABLA CON TU GRANJA") Y SALUD DE LA API
# ==============================================================================

class FarmChatRequest(BaseModel):
    """
    Petición para la función 'Habla con tu Granja'.
    """
    question: str = Field(..., description="Pregunta del agricultor en lenguaje natural")
    session_id: Optional[str] = Field("web_session_01", description="ID de sesión")


class FarmChatResponse(BaseModel):
    """
    Respuesta generada por el LLM con datos reales de la granja.
    """
    answer: str = Field(..., description="Respuesta explicativa del LLM")
    tools_consulted: List[str] = Field(default_factory=list, description="Tablas/métricas consultadas")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(BaseModel):
    """
    Respuesta para el probe de salud de Azure ACI.
    """
    status: str = "healthy"
    service: str = "AgroSense AI Cloud Backend"
    version: str = "1.0.0"
    environment: str = "development"
    engine_jev: str = "ONLINE"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
