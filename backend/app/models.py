from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


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
    growth_stage: str = Field("VEGETATIVO", description="Etapa fenológica")


class TelemetryInput(BaseModel):
    """
    Entidad TelemetryReading: Mediciones en tiempo real recibidas desde ESP32 / Sensores.
    """
    device_id: str = Field("esp32_nodo_01", description="ID del dispositivo en terreno")
    sector_id: str = Field("cuartel_01_avellanos", description="ID del sector")
    soil_moisture: float = Field(..., ge=0, le=100, description="Humedad de suelo (0 - 100%)")
    ambient_temperature: float = Field(..., description="Temperatura ambiental (°C)")
    soil_temperature: Optional[float] = Field(15.0, description="Temperatura radicular (°C)")
    ambient_humidity: Optional[float] = Field(65.0, ge=0, le=100, description="Humedad ambiental (%)")
    ph_level: Optional[float] = Field(6.2, ge=0, le=14, description="Acidez del suelo (0 - 14)")
    nitrogen_ppm: Optional[float] = Field(14.0, description="Nitrógeno (ppm)")
    phosphorus_ppm: Optional[float] = Field(8.0, description="Fósforo (ppm)")
    potassium_ppm: Optional[float] = Field(16.0, description="Potasio (ppm)")
    wind_speed_kmh: Optional[float] = Field(8.5, description="Velocidad del viento (km/h)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Marca temporal UTC")


class JevDecisionResponse(BaseModel):
    """
    Salida de decisión del Motor JEV:
    1. Booleano (true/false)
    2. Modulación de intensidad (0 - 100%)
    3. Selección de actuadores/herramientas de la lista
    """
    decision_action: bool = Field(..., description="¿Se activa maniobra? (true/false)")
    decision_intensity: int = Field(..., ge=0, le=100, description="Intensidad ordenada (0 - 100%)")
    commanded_tools: List[str] = Field(..., description="Herramientas comandadas de la flota")
    justification_reason: str = Field(..., description="Fundamentación determinista de la regla")
    lease_duration_seconds: int = Field(900, description="Tiempo de vigencia seguro (segundos)")
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de inferencia")
    failsafe_active: bool = Field(False, description="Si opera en modo de prevención")


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
    engine_jev: str = "ONLINE"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
