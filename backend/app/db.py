# ==============================================================================
# AGROSENSE AI — CAPA COMPARTIDA DE PERSISTENCIA SQLITE Y UTILIDADES
# ==============================================================================
# Fuente única de verdad para DB_PATH, cálculos fisiológicos (DPV Tetens)
# y lectura/escritura persistente del estado de módulos y calendario semanal.
# ==============================================================================

import json
import math
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agrosense.db"))
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database_schema.sql")

DIAS_SEMANA: List[str] = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_MAP: Dict[int, str] = {idx: dia for idx, dia in enumerate(DIAS_SEMANA)}


def get_connection() -> sqlite3.Connection:
    """Abre conexión SQLite compartida con RowFactory y foreign keys activas."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_today_es() -> str:
    """Retorna abreviatura en español del día actual (Lun..Dom)."""
    return DIAS_MAP[datetime.now().weekday()]


def calculate_vpd(temp_c: float, rh_pct: float) -> float:
    """Fórmula de Tetens para Déficit de Presión de Vapor (DPV) en kPa."""
    svp = 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))
    avp = svp * (rh_pct / 100.0)
    return round(svp - avp, 2)


def init_db() -> None:
    """Inicializa esquema DDL e inserta datos semilla idempotentes."""
    with get_connection() as conn:
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM telemetria_historica")
        if cursor.fetchone()[0] == 0:
            ahora = datetime.utcnow()
            seed_data = [
                ("celda-01", (ahora - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S"), 21.2, 64.0, 1014.0, 0.92, 88.0, 0, 0, 0),
                ("celda-01", (ahora - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"), 21.6, 63.1, 1014.2, 0.95, 86.5, 1, 0, 0),
                ("celda-01", ahora.strftime("%Y-%m-%d %H:%M:%S"), 21.8, 62.4, 1014.5, 0.98, 85.0, 0, 0, 0),
            ]
            cursor.executemany(
                """
                INSERT INTO telemetria_historica (
                    modulo_id, fecha_hora, temp_ambiente, humedad_ambiente, presion_atmosferica,
                    dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo, pasos_motor_acumulados
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                seed_data,
            )
            conn.commit()


def load_schedule(module_id: str) -> Dict[str, Any]:
    """Lee desde SQLite la configuración persistente del calendario del módulo."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM calendario_semanal WHERE modulo_id = ?",
            (module_id,),
        ).fetchone()
    if row is None:
        return {
            "dias_semana": DIAS_SEMANA,
            "active_days": ["Lun", "Mié", "Vie"] if module_id == "invernadero-orquideas" else list(DIAS_SEMANA),
            "irrigation_time": "08:30" if module_id == "invernadero-orquideas" else "08:00",
            "duration_minutes": 20 if module_id == "invernadero-orquideas" else 15,
            "interval_hours": 24 if module_id == "invernadero-orquideas" else 2,
        }
    return {
        "dias_semana": DIAS_SEMANA,
        "active_days": json.loads(row["dias_activos_json"]),
        "irrigation_time": row["hora_riego"],
        "duration_minutes": row["duracion_minutos"],
        "interval_hours": row["intervalo_horas"],
    }


def save_schedule(
    module_id: str,
    active_days: Optional[List[str]] = None,
    irrigation_time: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    interval_hours: Optional[int] = None,
) -> Dict[str, Any]:
    """Persiste el calendario semanal o de recirculación en SQLite."""
    current = load_schedule(module_id)
    new_days = active_days if active_days is not None else current["active_days"]
    new_time = irrigation_time if irrigation_time is not None else current["irrigation_time"]
    new_dur = duration_minutes if duration_minutes is not None else current["duration_minutes"]
    new_int = interval_hours if interval_hours is not None else current["interval_hours"]

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO calendario_semanal (modulo_id, dias_activos_json, hora_riego, duracion_minutos, intervalo_horas, actualizado_en)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(modulo_id) DO UPDATE SET
                dias_activos_json = excluded.dias_activos_json,
                hora_riego = excluded.hora_riego,
                duracion_minutos = excluded.duracion_minutos,
                intervalo_horas = excluded.intervalo_horas,
                actualizado_en = CURRENT_TIMESTAMP
            """,
            (module_id, json.dumps(new_days, ensure_ascii=False), new_time, new_dur, new_int),
        )
        conn.commit()
    return load_schedule(module_id)


def load_module_state(module_id: str) -> Dict[str, Any]:
    """Lee el último estado operativo persistido de un módulo físico."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM estado_modulo WHERE modulo_id = ?",
            (module_id,),
        ).fetchone()
    if row is None:
        return {
            "module_id": module_id,
            "air_temperature": 21.8,
            "air_humidity": 62.4,
            "barometric_pressure_hpa": 1014.5,
            "reservoir_level_percent": 85.0,
            "vpd_kpa": 0.98,
            "pump_active": False,
            "vent_servo_angle": 0,
            "stepper_dosing_steps": 0,
            "soil_humidity_pct": 68.0 if module_id == "invernadero-orquideas" else None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    return {
        "module_id": row["modulo_id"],
        "air_temperature": row["temp_ambiente"],
        "air_humidity": row["humedad_ambiente"],
        "barometric_pressure_hpa": row["presion_hpa"],
        "reservoir_level_percent": row["nivel_estanque"],
        "vpd_kpa": row["dpv_kpa"] if row["dpv_kpa"] is not None else calculate_vpd(row["temp_ambiente"], row["humedad_ambiente"]),
        "pump_active": bool(row["bomba_encendida"]),
        "vent_servo_angle": int(row["servo_angulo"]),
        "stepper_dosing_steps": int(row["pasos_motor_acumulados"]),
        "soil_humidity_pct": row["humedad_sustrato"],
        "timestamp": row["actualizado_en"],
    }


def save_module_state(module_id: str, **updates: Any) -> Dict[str, Any]:
    """Actualiza y persiste en SQLite el estado operativo de un módulo."""
    current = load_module_state(module_id)
    current.update({k: v for k, v in updates.items() if v is not None})
    if updates.get("vpd_kpa") is None and ("air_temperature" in updates or "air_humidity" in updates):
        current["vpd_kpa"] = calculate_vpd(current["air_temperature"], current["air_humidity"])

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO estado_modulo (
                modulo_id, temp_ambiente, humedad_ambiente, presion_hpa,
                nivel_estanque, dpv_kpa, bomba_encendida, servo_angulo,
                pasos_motor_acumulados, humedad_sustrato, actualizado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(modulo_id) DO UPDATE SET
                temp_ambiente = excluded.temp_ambiente,
                humedad_ambiente = excluded.humedad_ambiente,
                presion_hpa = excluded.presion_hpa,
                nivel_estanque = excluded.nivel_estanque,
                dpv_kpa = excluded.dpv_kpa,
                bomba_encendida = excluded.bomba_encendida,
                servo_angulo = excluded.servo_angulo,
                pasos_motor_acumulados = excluded.pasos_motor_acumulados,
                humedad_sustrato = excluded.humedad_sustrato,
                actualizado_en = excluded.actualizado_en
            """,
            (
                module_id,
                current["air_temperature"],
                current["air_humidity"],
                current["barometric_pressure_hpa"],
                current["reservoir_level_percent"],
                current["vpd_kpa"],
                1 if current["pump_active"] else 0,
                current["vent_servo_angle"],
                current["stepper_dosing_steps"],
                current["soil_humidity_pct"],
                now_str,
            ),
        )
        conn.commit()
    return load_module_state(module_id)


def insert_telemetry(
    module_id: str,
    temp: float,
    humidity: float,
    pressure: float,
    vpd: Optional[float],
    level: float,
    pump_active: bool,
    servo_angle: int,
    steps: int,
    origen: str = "MQTT_ESP32",
) -> None:
    """Inserta una lectura de serie temporal en telemetria_historica."""
    computed_vpd = vpd if vpd is not None else calculate_vpd(temp, humidity)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO telemetria_historica (
                modulo_id, temp_ambiente, humedad_ambiente, presion_atmosferica,
                dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo,
                pasos_motor_acumulados, origen_dato
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (module_id, temp, humidity, pressure, computed_vpd, level, 1 if pump_active else 0, servo_angle, steps, origen),
        )
        conn.commit()


def insert_command_audit(
    module_id: str,
    target: str,
    action: str,
    parameter_value: Optional[float],
    triggered_by: str,
) -> None:
    """Registra una auditoría de comando ejecutado sobre actuadores o calendario."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO registro_comandos (
                modulo_id, actuador, accion, parametro_valor, disparado_por
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (module_id, target, action, parameter_value or 0.0, triggered_by),
        )
        conn.commit()


def get_telemetry_history(limit: int = 10, module_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consulta las últimas lecturas históricas registradas en SQLite."""
    with get_connection() as conn:
        if module_id:
            rows = conn.execute(
                """
                SELECT id, modulo_id, fecha_hora, temp_ambiente, humedad_ambiente,
                       presion_atmosferica, dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo
                FROM telemetria_historica
                WHERE modulo_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (module_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, modulo_id, fecha_hora, temp_ambiente, humedad_ambiente,
                       presion_atmosferica, dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo
                FROM telemetria_historica
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]
