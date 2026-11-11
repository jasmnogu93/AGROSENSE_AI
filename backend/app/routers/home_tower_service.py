# ==============================================================================
# AGROSENSE AI — SERVICIO 2: HOMETOWER SERVICE (MINI TORRES DOMICILIARIAS)
# ==============================================================================
# Propósito: Agricultura Urbana en Hogares — Proyecto Feria de Innovación Santo Tomás
# Cátedras integradas: Programación Android (IEI-058) & Internet de las Cosas (IEI-059)
# ==============================================================================

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db

router = APIRouter()

# Comparte el identificador de hardware físico con main.py y el ESP32 ('celda-01')
MODULE_ID = "celda-01"

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
    "nivel_estanque_min_seguro": 20.0,
}


class RecirculationUpdate(BaseModel):
    interval_hours: int = Field(..., ge=1, le=24, description="Frecuencia en horas entre riegos")
    duration_minutes: int = Field(..., ge=1, le=120, description="Duración de bombeo en minutos")


class ActuatorCommandInput(BaseModel):
    target: str = Field(..., description="bomba_agua | servo_ventilacion | motor_nutrientes")
    action: str = Field(..., description="ON | OFF | SET_ANGLE | DISPENSE_STEPS")
    parameter_value: Optional[float] = Field(default=0.0)
    triggered_by: str = Field(default="ANDROID_APP")


def get_home_tower_dashboard_data() -> Dict[str, Any]:
    """Lee el estado persistido de la Mini Torre Domiciliaria para el dashboard."""
    state = db.load_module_state(MODULE_ID)
    sched = db.load_schedule(MODULE_ID)
    return {
        "profile": HOME_TOWER_PROFILE,
        "state": {
            "module_id": MODULE_ID,
            "name": "Mini Torre Domiciliaria ASAI (Celda 01)",
            "location": "Hogar Urbano - Balcón / Cocina",
            "air_temperature": state["air_temperature"],
            "air_humidity": state["air_humidity"],
            "barometric_pressure_hpa": state["barometric_pressure_hpa"],
            "reservoir_level_percent": state["reservoir_level_percent"],
            "dpv_kpa": state["vpd_kpa"],
            "pump_active": state["pump_active"],
            "vent_servo_angle": state["vent_servo_angle"],
            "nutrient_dosing_steps": state["stepper_dosing_steps"],
            "recirculation_interval_hours": sched["interval_hours"],
            "recirculation_duration_minutes": sched["duration_minutes"],
            "last_cycle_timestamp": state["timestamp"],
        },
    }


def apply_actuator_command_persistent(
    module_id: str,
    target: str,
    action: str,
    parameter_value: Optional[float],
    triggered_by: str,
    enforce_cavitation_lock: bool = True,
) -> Dict[str, Any]:
    """Ejecuta un comando de actuador aplicando seguridad anti-cavitación y persistencia SQLite."""
    state = db.load_module_state(module_id)
    updates: Dict[str, Any] = {}
    act_upper = action.upper()

    if target == "bomba_agua":
        if act_upper == "ON":
            if enforce_cavitation_lock and state["reservoir_level_percent"] < HOME_TOWER_PROFILE["nivel_estanque_min_seguro"]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"COMANDO RECHAZADO: Estanque en nivel crítico "
                        f"({state['reservoir_level_percent']:.1f}% < 20.0%). "
                        f"Bomba bloqueada por seguridad para evitar quemar el motor."
                    ),
                )
            updates["pump_active"] = True
        elif act_upper == "OFF":
            updates["pump_active"] = False
    elif target == "servo_ventilacion":
        angle = max(0, min(180, int(parameter_value or 0)))
        updates["vent_servo_angle"] = angle
    elif target == "motor_nutrientes":
        steps = max(0, int(parameter_value or 0))
        updates["stepper_dosing_steps"] = state["stepper_dosing_steps"] + steps
    else:
        raise HTTPException(status_code=400, detail=f"Actuador '{target}' no reconocido.")

    new_state = db.save_module_state(module_id, **updates)
    db.insert_command_audit(module_id, target, action, parameter_value, triggered_by)
    db.insert_telemetry(
        module_id=module_id,
        temp=new_state["air_temperature"],
        humidity=new_state["air_humidity"],
        pressure=new_state["barometric_pressure_hpa"],
        vpd=new_state["vpd_kpa"],
        level=new_state["reservoir_level_percent"],
        pump_active=new_state["pump_active"],
        servo_angle=new_state["vent_servo_angle"],
        steps=new_state["stepper_dosing_steps"],
        origen=triggered_by,
    )
    return new_state


# ==============================================================================
# ENDPOINTS REST: HOMETOWER SERVICE
# ==============================================================================

@router.get("/status")
async def get_home_tower_status():
    """Retorna el estado integral persistido de la mini torre domiciliaria."""
    data = get_home_tower_dashboard_data()
    st = data["state"]
    next_cycle = datetime.now() + timedelta(hours=st["recirculation_interval_hours"])
    level = st["reservoir_level_percent"]
    cavitacion_risk = level < HOME_TOWER_PROFILE["nivel_estanque_min_seguro"]

    return {
        "service": "HomeTower Service (Mini Torres Domiciliarias)",
        "project": "Feria de Innovación Santo Tomás & Android IEI-058",
        "tower_info": {
            "module_id": st["module_id"],
            "name": st["name"],
            "crop": HOME_TOWER_PROFILE["especie"],
        },
        "telemetry": {
            "temperature_c": st["air_temperature"],
            "humidity_pct": st["air_humidity"],
            "pressure_hpa": st["barometric_pressure_hpa"],
            "reservoir_level_pct": level,
            "dpv_kpa": st["dpv_kpa"],
        },
        "actuators": {
            "pump_active": st["pump_active"],
            "vent_servo_angle": st["vent_servo_angle"],
            "nutrient_steps": st["nutrient_dosing_steps"],
        },
        "recirculation": {
            "interval_hours": st["recirculation_interval_hours"],
            "duration_minutes": st["recirculation_duration_minutes"],
            "next_cycle_time": next_cycle.strftime("%H:%M:%S"),
            "status": "BOMBEANDO" if st["pump_active"] else "EN_ESPERA",
        },
        "safety": {
            "status": "CRITICAL" if cavitacion_risk else "NORMAL",
            "pump_allowed": not cavitacion_risk,
            "message": "BLOQUEO ANTI-CAVITACIÓN: Nivel crítico (<20%). Bomba protegida." if cavitacion_risk else "Nivel de solución óptimo.",
        },
    }


@router.post("/recirculation")
async def update_recirculation_params(data: RecirculationUpdate):
    """Configura y persiste los ciclos periódicos de recirculación en SQLite."""
    saved = db.save_schedule(
        MODULE_ID,
        duration_minutes=data.duration_minutes,
        interval_hours=data.interval_hours,
    )
    next_cycle = datetime.now() + timedelta(hours=saved["interval_hours"])
    return {
        "status": "success",
        "message": f"Ciclo de mini torre actualizado: cada {saved['interval_hours']}h durante {saved['duration_minutes']} min.",
        "interval_hours": saved["interval_hours"],
        "duration_minutes": saved["duration_minutes"],
        "next_cycle_time": next_cycle.strftime("%H:%M:%S"),
    }


@router.post("/actuators/command")
async def execute_actuator_command(cmd: ActuatorCommandInput):
    """Envía comando a los actuadores físicos de la mini torre con protección anti-cavitación."""
    new_state = apply_actuator_command_persistent(
        module_id=MODULE_ID,
        target=cmd.target,
        action=cmd.action,
        parameter_value=cmd.parameter_value,
        triggered_by=cmd.triggered_by,
        enforce_cavitation_lock=True,
    )
    return {
        "status": "success",
        "actuator": cmd.target,
        "action": cmd.action,
        "parameter_value": cmd.parameter_value,
        "triggered_by": cmd.triggered_by,
        "pump_active": new_state["pump_active"],
        "vent_servo_angle": new_state["vent_servo_angle"],
        "stepper_dosing_steps": new_state["stepper_dosing_steps"],
        "message": f"Comando '{cmd.action}' ejecutado exitosamente en {cmd.target}.",
    }


@router.get("/safety-check")
async def evaluate_safety():
    """Evalúa reglas ciberfísicas deterministas sobre la mini torre."""
    state = db.load_module_state(MODULE_ID)
    level = state["reservoir_level_percent"]
    temp = state["air_temperature"]
    dpv = state["vpd_kpa"]

    if level < HOME_TOWER_PROFILE["nivel_estanque_min_seguro"]:
        return {
            "risk_level": "CRITICAL",
            "action_required": True,
            "pump_state": False,
            "servo_angle": state["vent_servo_angle"],
            "reason": f"Alerta crítica: Nivel de estanque en {level:.1f}%. Bomba bloqueada.",
        }
    if temp > HOME_TOWER_PROFILE["temp_optima_max"] or dpv > HOME_TOWER_PROFILE["dpv_optimo_max_kpa"]:
        return {
            "risk_level": "WARNING",
            "action_required": True,
            "pump_state": state["pump_active"],
            "servo_angle": 90,
            "reason": f"Alivio térmico: Temperatura ({temp:.1f}°C) o DPV ({dpv:.2f} kPa) excedidos. Servo a 90°.",
        }
    return {
        "risk_level": "NORMAL",
        "action_required": False,
        "pump_state": state["pump_active"],
        "servo_angle": 0,
        "reason": "Condiciones fisiológicas y mecánicas óptimas en la torre.",
    }
