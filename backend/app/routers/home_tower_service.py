# ==============================================================================
# AGROSENSE AI — SERVICIO 2: HOMETOWER SERVICE (MINI TORRES DOMICILIARIAS)
# ==============================================================================
# Propósito: Agricultura Urbana en Hogares — Proyecto Feria de Innovación Santo Tomás
# Cátedras integradas: Programación Android (IEI-058) & Internet de las Cosas (IEI-059)
# ==============================================================================

import os
import sqlite3
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "agrosense.db")

# Estado en memoria de la Mini Torre Domiciliaria Piloto
HOME_TOWER_PROFILE = {
    "especie": "Frutilla Hidropónica (Fragaria x ananassa)",
    "variedad": "Albion / San Andreas",
    "sistema": "Mini Torre Vertical NFT / Sustrato Inerte",
    "temp_optima_min": 18.0,
    "temp_optima_max": 24.0,
    "humedad_optima_min": 55.0,
    "humedad_optima_max": 75.0,
    "dpv_optimo_min_kpa": 0.8,
    "dpv_optimo_max_kpa": 1.2,
    "nivel_estanque_min_seguro": 20.0
}

home_tower_state = {
    "module_id": "mini-torre-01",
    "name": "Mini Torre Domiciliaria ASAI",
    "location": "Hogar Urbano - Balcón / Cocina",
    "air_temperature": 22.1,
    "air_humidity": 63.5,
    "barometric_pressure_hpa": 1014.2,
    "reservoir_level_percent": 82.0,
    "dpv_kpa": 0.97,
    "pump_active": False,
    "vent_servo_angle": 0,
    "nutrient_dosing_steps": 0,
    "recirculation_interval_hours": 2,
    "recirculation_duration_minutes": 15,
    "last_cycle_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}


class RecirculationUpdate(BaseModel):
    interval_hours: int = Field(..., ge=1, le=24, description="Frecuencia en horas entre riegos")
    duration_minutes: int = Field(..., ge=1, le=120, description="Duración de bombeo en minutos")


class ActuatorCommand(BaseModel):
    target: str = Field(..., description="bomba_agua | servo_ventilacion | motor_nutrientes")
    action: str = Field(..., description="ON | OFF | SET_ANGLE | DISPENSE_STEPS")
    parameter_value: Optional[float] = Field(default=0.0)
    triggered_by: str = Field(default="ANDROID_APP")


def calculate_vpd(temp_c: float, rh_pct: float) -> float:
    svp = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    avp = svp * (rh_pct / 100.0)
    return round(svp - avp, 2)


# ==============================================================================
# ENDPOINTS REST: HOMETOWER SERVICE
# ==============================================================================

@router.get("/status")
async def get_home_tower_status():
    """Retorna el estado integral de la mini torre domiciliaria."""
    # Calcular próximo ciclo de recirculación
    next_cycle = datetime.now() + timedelta(hours=home_tower_state["recirculation_interval_hours"])
    
    # Evaluar seguridad de la bomba
    level = home_tower_state["reservoir_level_percent"]
    cavitacion_risk = level < HOME_TOWER_PROFILE["nivel_estanque_min_seguro"]

    return {
        "service": "HomeTower Service (Mini Torres Domiciliarias)",
        "project": "Feria de Innovación Santo Tomás & Android IEI-058",
        "tower_info": {
            "module_id": home_tower_state["module_id"],
            "name": home_tower_state["name"],
            "crop": HOME_TOWER_PROFILE["especie"]
        },
        "telemetry": {
            "temperature_c": home_tower_state["air_temperature"],
            "humidity_pct": home_tower_state["air_humidity"],
            "pressure_hpa": home_tower_state["barometric_pressure_hpa"],
            "reservoir_level_pct": home_tower_state["reservoir_level_percent"],
            "dpv_kpa": home_tower_state["dpv_kpa"]
        },
        "actuators": {
            "pump_active": home_tower_state["pump_active"],
            "vent_servo_angle": home_tower_state["vent_servo_angle"],
            "nutrient_steps": home_tower_state["nutrient_dosing_steps"]
        },
        "recirculation": {
            "interval_hours": home_tower_state["recirculation_interval_hours"],
            "duration_minutes": home_tower_state["recirculation_duration_minutes"],
            "next_cycle_time": next_cycle.strftime("%H:%M:%S"),
            "status": "BOMBEANDO" if home_tower_state["pump_active"] else "EN_ESPERA"
        },
        "safety": {
            "status": "CRITICAL" if cavitacion_risk else "NORMAL",
            "pump_allowed": not cavitacion_risk,
            "message": "BLOQUEO ANTI-CAVITACIÓN: Nivel crítico (<20%). Bomba protegida." if cavitacion_risk else "Nivel de solución óptimo."
        }
    }


@router.post("/recirculation")
async def update_recirculation_params(data: RecirculationUpdate):
    """Configura los ciclos periódicos de recirculación de solución hidropónica."""
    global home_tower_state
    home_tower_state["recirculation_interval_hours"] = data.interval_hours
    home_tower_state["recirculation_duration_minutes"] = data.duration_minutes
    
    next_cycle = datetime.now() + timedelta(hours=data.interval_hours)
    
    return {
        "status": "success",
        "message": f"Ciclo de mini torre actualizado: cada {data.interval_hours}h durante {data.duration_minutes} min.",
        "interval_hours": data.interval_hours,
        "duration_minutes": data.duration_minutes,
        "next_cycle_time": next_cycle.strftime("%H:%M:%S")
    }


@router.post("/actuators/command")
async def execute_actuator_command(cmd: ActuatorCommand):
    """Envía un comando directo a los actuadores físicos de la mini torre (Bomba, Servo, PaP)."""
    global home_tower_state
    
    # 1. Regla crítica de hardware: Anti-cavitación en la mini-bomba
    if cmd.target == "bomba_agua" and cmd.action.upper() == "ON":
        if home_tower_state["reservoir_level_percent"] < HOME_TOWER_PROFILE["nivel_estanque_min_seguro"]:
            raise HTTPException(
                status_code=400,
                detail=f"COMANDO RECHAZADO: Estanque en nivel crítico ({home_tower_state['reservoir_level_percent']} < 20%). "
                       f"Bomba bloqueada por seguridad para evitar quemar el motor."
            )
        home_tower_state["pump_active"] = True
    elif cmd.target == "bomba_agua" and cmd.action.upper() == "OFF":
        home_tower_state["pump_active"] = False
    elif cmd.target == "servo_ventilacion":
        home_tower_state["vent_servo_angle"] = int(cmd.parameter_value or 0)
    elif cmd.target == "motor_nutrientes":
        home_tower_state["nutrient_dosing_steps"] += int(cmd.parameter_value or 0)

    # Registrar en base de datos SQLite para auditoría
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO registro_comandos (modulo_id, actuador, accion, parametro_valor, disparado_por)
            VALUES (?, ?, ?, ?, ?)
        """, (home_tower_state["module_id"], cmd.target, cmd.action, cmd.parameter_value, cmd.triggered_by))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error registrando comando en SQLite: {e}")

    return {
        "status": "success",
        "actuator": cmd.target,
        "action": cmd.action,
        "parameter_value": cmd.parameter_value,
        "triggered_by": cmd.triggered_by,
        "message": f"Comando '{cmd.action}' ejecutado exitosamente en {cmd.target}."
    }


@router.get("/safety-check")
async def evaluate_safety():
    """Evalúa las reglas ciberfísicas de seguridad para la mini torre doméstica."""
    level = home_tower_state["reservoir_level_percent"]
    temp = home_tower_state["air_temperature"]
    dpv = home_tower_state["dpv_kpa"]
    
    if level < 20.0:
        return {
            "risk_level": "CRITICAL",
            "action_required": True,
            "pump_state": False,
            "servo_angle": home_tower_state["vent_servo_angle"],
            "reason": f"Alerta crítica: Nivel de estanque en {level:.1f}%. Bomba bloqueada."
        }
    elif temp > HOME_TOWER_PROFILE["temp_optima_max"] or dpv > HOME_TOWER_PROFILE["dpv_optimo_max_kpa"]:
        return {
            "risk_level": "WARNING",
            "action_required": True,
            "pump_state": home_tower_state["pump_active"],
            "servo_angle": 90,
            "reason": f"Alivio térmico: Temperatura ({temp:.1f}°C) o DPV ({dpv:.2f} kPa) excedidos. Servo a 90°."
        }
    else:
        return {
            "risk_level": "NORMAL",
            "action_required": False,
            "pump_state": home_tower_state["pump_active"],
            "servo_angle": 0,
            "reason": "Condiciones fisiológicas y mecánicas óptimas en la torre."
        }
