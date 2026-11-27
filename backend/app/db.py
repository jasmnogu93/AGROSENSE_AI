# ==============================================================================
# AGROSENSE AI — MÓDULO DE BASE DE DATOS (SUPABASE CLOUD + RESPALDO SQLITE)
# ==============================================================================
# En este archivo implementamos la conexión de datos del sistema (RF6):
# - En ejecución normal se conecta vía HTTPS (PostgREST) a Supabase PostgreSQL
#   usando las credenciales definidas en backend/.env.
# - Si se ejecutan pruebas aisladas (pytest) o cae la red, respalda en SQLite local.
# ==============================================================================

import json
import logging
import math
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger("asai.db")

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agrosense.db"))
_DEFAULT_DB_PATH = DB_PATH
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database_schema.sql")

DIAS_SEMANA: List[str] = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIAS_MAP: Dict[int, str] = {idx: dia for idx, dia in enumerate(DIAS_SEMANA)}

_sb_client: Optional[httpx.Client] = None
_supabase_schema_missing: bool = False
_supabase_last_error: Optional[str] = None
_ALLOW_SUPABASE_FOR_TEST: bool = False


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
    return round(max(0.0, svp - avp), 2)


def _format_ts(val: Optional[str]) -> str:
    """Normaliza timestamps ISO (Supabase TIMESTAMPTZ) o SQLite a 'YYYY-MM-DD HH:MM:SS'."""
    if not val:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = str(val).strip()
    if "T" in text:
        try:
            iso = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return text[:19].replace("T", " ")
    return text[:19]


def _get_sb_client() -> httpx.Client:
    global _sb_client
    if _sb_client is None:
        _sb_client = httpx.Client(timeout=6.0)
    return _sb_client


def _is_supabase_configured() -> bool:
    """Usa Supabase en la nube salvo en pruebas pytest aisladas (donde DB_PATH apunta a tmp_path)."""
    if not (settings.SUPABASE_URL and settings.SUPABASE_KEY):
        return False
    if DB_PATH != _DEFAULT_DB_PATH and not _ALLOW_SUPABASE_FOR_TEST:
        return False
    return True


def _use_supabase() -> bool:
    return _is_supabase_configured() and not _supabase_schema_missing


def _sb_headers(prefer: Optional[str] = None) -> Dict[str, str]:
    """Arma las cabeceras HTTP requeridas por la API REST (PostgREST) de Supabase."""
    headers = {
        "apikey": settings.SUPABASE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _sb_request(
    method: str,
    table: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Any] = None,
    prefer: Optional[str] = None,
) -> Optional[Any]:
    """Envía peticiones HTTPS a PostgREST de Supabase; ante fallo de red cae de forma segura a SQLite."""
    global _supabase_schema_missing, _supabase_last_error
    url = f"{settings.SUPABASE_URL}/rest/v1/{table}"
    try:
        resp = _get_sb_client().request(
            method,
            url,
            headers=_sb_headers(prefer),
            params=params,
            json=json_body,
        )
        if resp.status_code in (200, 201, 204):
            _supabase_schema_missing = False
            _supabase_last_error = None
            return resp.json() if resp.text.strip() else []
        body_txt = resp.text[:250]
        if resp.status_code == 404 and "PGRST205" in body_txt:
            _supabase_schema_missing = True
            _supabase_last_error = "Falta ejecutar database_schema_supabase.sql en Supabase SQL Editor."
        else:
            _supabase_last_error = f"HTTP {resp.status_code}: {body_txt}"
        logger.warning(f"Supabase {method} {table} fallo ({resp.status_code}): {body_txt}")
        return None
    except Exception as exc:
        _supabase_last_error = str(exc)
        logger.warning(f"Error de red conectando a Supabase ({table}): {exc}")
        return None


def get_storage_backend_info() -> Dict[str, Any]:
    """Retorna estado real del motor de persistencia activo para el UI y /health."""
    global _supabase_schema_missing
    if not _is_supabase_configured():
        return {
            "engine": "SQLite Local",
            "cloud": False,
            "connected": True,
            "label": "SQLite Activa",
            "detail": "Base relacional local (agrosense.db).",
        }
    # Re-verificar si faltaban tablas por crear en Supabase
    res = _sb_request("GET", "modulos_hidroponicos", params={"select": "id", "limit": 1})
    if res is not None:
        _supabase_schema_missing = False
        return {
            "engine": "Supabase (PostgreSQL)",
            "cloud": True,
            "connected": True,
            "label": "Supabase Cloud",
            "detail": f"Conectado a {settings.SUPABASE_URL}",
        }
    if _supabase_schema_missing:
        return {
            "engine": "SQLite Local (Respaldo)",
            "cloud": False,
            "connected": False,
            "label": "Supabase: Falta SQL",
            "detail": _supabase_last_error or "Ejecuta database_schema_supabase.sql en Supabase.",
        }
    return {
        "engine": "SQLite Local (Respaldo)",
        "cloud": False,
        "connected": False,
        "label": "SQLite Respaldo",
        "detail": _supabase_last_error or "Sin respuesta de Supabase; operando en respaldo local.",
    }


def init_db() -> None:
    """Inicializa esquema DDL SQLite local y verifica conexión Supabase si aplica."""
    with get_connection() as conn:
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())

        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(estado_modulo)")
        existing_estado = {row["name"] for row in cursor.fetchall()}
        if "ext_temp_ambiente" not in existing_estado:
            conn.execute("ALTER TABLE estado_modulo ADD COLUMN ext_temp_ambiente REAL;")
        if "ext_humedad_ambiente" not in existing_estado:
            conn.execute("ALTER TABLE estado_modulo ADD COLUMN ext_humedad_ambiente REAL;")

        cursor.execute("PRAGMA table_info(calendario_semanal)")
        existing_cal = {row["name"] for row in cursor.fetchall()}
        if "frecuencia_registro_min" not in existing_cal:
            conn.execute("ALTER TABLE calendario_semanal ADD COLUMN frecuencia_registro_min INTEGER NOT NULL DEFAULT 60;")

        cursor.execute("SELECT COUNT(*) FROM telemetria_historica")
        if cursor.fetchone()[0] == 0:
            ahora = datetime.utcnow()
            seed_data = [
                ("celda-01", (ahora - timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M:%S"), 21.2, 64.0, 1014.0, 0.92, 88.0, 0, 0, 0, "SEED_INICIAL"),
                ("celda-01", (ahora - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S"), 21.6, 63.1, 1014.2, 0.95, 86.5, 1, 0, 0, "SEED_INICIAL"),
                ("celda-01", ahora.strftime("%Y-%m-%d %H:%M:%S"), 21.8, 62.4, 1014.5, 0.98, 85.0, 0, 0, 0, "SEED_INICIAL"),
                ("invernadero-orquideas", (ahora - timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S"), 21.0, 79.2, 1013.5, 0.52, 100.0, 0, 0, 0, "SEED_INICIAL"),
                ("invernadero-orquideas", ahora.strftime("%Y-%m-%d %H:%M:%S"), 21.4, 79.8, 1013.8, 0.52, 100.0, 0, 0, 0, "SEED_INICIAL"),
            ]
            cursor.executemany(
                """
                INSERT INTO telemetria_historica (
                    modulo_id, fecha_hora, temp_ambiente, humedad_ambiente, presion_atmosferica,
                    dpv_kpa, nivel_estanque, bomba_encendida, servo_angulo, pasos_motor_acumulados, origen_dato
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                seed_data,
            )
            conn.commit()

    if _is_supabase_configured():
        info = get_storage_backend_info()
        logger.info(f"Persistencia inicializada: {info['label']} ({info['detail']})")


def _default_schedule(module_id: str) -> Dict[str, Any]:
    return {
        "dias_semana": DIAS_SEMANA,
        "active_days": ["Lun", "Mié", "Vie"] if module_id == "invernadero-orquideas" else list(DIAS_SEMANA),
        "irrigation_time": "08:30" if module_id == "invernadero-orquideas" else "08:00",
        "duration_minutes": 20 if module_id == "invernadero-orquideas" else 15,
        "interval_hours": 24 if module_id == "invernadero-orquideas" else 2,
        "recording_frequency_minutes": 60 if module_id == "invernadero-orquideas" else 15,
    }


def load_schedule(module_id: str) -> Dict[str, Any]:
    """Lee la configuración persistente del calendario semanal y frecuencia del módulo."""
    if _use_supabase():
        rows = _sb_request(
            "GET",
            "calendario_semanal",
            params={"modulo_id": f"eq.{module_id}", "select": "*"},
        )
        if isinstance(rows, list):
            if not rows:
                return _default_schedule(module_id)
            row = rows[0]
            return {
                "dias_semana": DIAS_SEMANA,
                "active_days": json.loads(row["dias_activos_json"]),
                "irrigation_time": row["hora_riego"],
                "duration_minutes": int(row["duracion_minutos"]),
                "interval_hours": int(row["intervalo_horas"]),
                "recording_frequency_minutes": int(row.get("frecuencia_registro_min") or 60),
            }

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM calendario_semanal WHERE modulo_id = ?",
            (module_id,),
        ).fetchone()
    if row is None:
        return _default_schedule(module_id)
    freq = row["frecuencia_registro_min"] if "frecuencia_registro_min" in row.keys() and row["frecuencia_registro_min"] is not None else 60
    return {
        "dias_semana": DIAS_SEMANA,
        "active_days": json.loads(row["dias_activos_json"]),
        "irrigation_time": row["hora_riego"],
        "duration_minutes": int(row["duracion_minutos"]),
        "interval_hours": int(row["intervalo_horas"]),
        "recording_frequency_minutes": int(freq),
    }


def save_schedule(
    module_id: str,
    active_days: Optional[List[str]] = None,
    irrigation_time: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    interval_hours: Optional[int] = None,
    recording_frequency_minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """Persiste el calendario semanal, recirculación o frecuencia de registro en BD."""
    current = load_schedule(module_id)
    new_days = active_days if active_days is not None else current["active_days"]
    new_time = irrigation_time if irrigation_time is not None else current["irrigation_time"]
    new_dur = duration_minutes if duration_minutes is not None else current["duration_minutes"]
    new_int = interval_hours if interval_hours is not None else current["interval_hours"]
    new_freq = recording_frequency_minutes if recording_frequency_minutes is not None else current["recording_frequency_minutes"]
    days_json = json.dumps(new_days, ensure_ascii=False)

    if _use_supabase():
        payload = {
            "modulo_id": module_id,
            "dias_activos_json": days_json,
            "hora_riego": new_time,
            "duracion_minutos": new_dur,
            "intervalo_horas": new_int,
            "frecuencia_registro_min": new_freq,
            "actualizado_en": datetime.utcnow().isoformat() + "Z",
        }
        # Usamos upsert en PostgREST ('on_conflict' + 'merge-duplicates') para actualizar
        # la fila si modulo_id ya existe o crearla si es el primer guardado.
        res = _sb_request(
            "POST",
            "calendario_semanal",
            params={"on_conflict": "modulo_id"},
            json_body=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        if res is not None:
            return load_schedule(module_id)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO calendario_semanal (
                modulo_id, dias_activos_json, hora_riego, duracion_minutos,
                intervalo_horas, frecuencia_registro_min, actualizado_en
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(modulo_id) DO UPDATE SET
                dias_activos_json = excluded.dias_activos_json,
                hora_riego = excluded.hora_riego,
                duracion_minutos = excluded.duracion_minutos,
                intervalo_horas = excluded.intervalo_horas,
                frecuencia_registro_min = excluded.frecuencia_registro_min,
                actualizado_en = CURRENT_TIMESTAMP
            """,
            (module_id, days_json, new_time, new_dur, new_int, new_freq),
        )
        conn.commit()
    return load_schedule(module_id)


def _default_module_state(module_id: str) -> Dict[str, Any]:
    return {
        "module_id": module_id,
        "air_temperature": 21.4 if module_id == "invernadero-orquideas" else 21.8,
        "air_humidity": 79.8 if module_id == "invernadero-orquideas" else 62.4,
        "barometric_pressure_hpa": 1013.8 if module_id == "invernadero-orquideas" else 1014.5,
        "reservoir_level_percent": 100.0 if module_id == "invernadero-orquideas" else 85.0,
        "vpd_kpa": 0.52 if module_id == "invernadero-orquideas" else 0.98,
        "pump_active": False,
        "vent_servo_angle": 0,
        "stepper_dosing_steps": 0,
        "soil_humidity_pct": 68.0 if module_id == "invernadero-orquideas" else None,
        "ext_temperature": None,
        "ext_humidity": None,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def load_module_state(module_id: str) -> Dict[str, Any]:
    """Lee el último estado operativo persistido de un módulo físico."""
    if _use_supabase():
        rows = _sb_request(
            "GET",
            "estado_modulo",
            params={"modulo_id": f"eq.{module_id}", "select": "*"},
        )
        if isinstance(rows, list):
            if not rows:
                return _default_module_state(module_id)
            row = rows[0]
            temp = float(row["temp_ambiente"])
            hum = float(row["humedad_ambiente"])
            return {
                "module_id": row["modulo_id"],
                "air_temperature": temp,
                "air_humidity": hum,
                "barometric_pressure_hpa": float(row.get("presion_hpa") or 1013.25),
                "reservoir_level_percent": float(row.get("nivel_estanque") or 85.0),
                "vpd_kpa": float(row["dpv_kpa"]) if row.get("dpv_kpa") is not None else calculate_vpd(temp, hum),
                "pump_active": bool(row.get("bomba_encendida")),
                "vent_servo_angle": int(row.get("servo_angulo") or 0),
                "stepper_dosing_steps": int(row.get("pasos_motor_acumulados") or 0),
                "soil_humidity_pct": float(row["humedad_sustrato"]) if row.get("humedad_sustrato") is not None else None,
                "ext_temperature": float(row["ext_temp_ambiente"]) if row.get("ext_temp_ambiente") is not None else None,
                "ext_humidity": float(row["ext_humedad_ambiente"]) if row.get("ext_humedad_ambiente") is not None else None,
                "timestamp": _format_ts(row.get("actualizado_en")),
            }

    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM estado_modulo WHERE modulo_id = ?",
            (module_id,),
        ).fetchone()
    if row is None:
        return _default_module_state(module_id)
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
        "ext_temperature": row["ext_temp_ambiente"] if "ext_temp_ambiente" in row.keys() else None,
        "ext_humidity": row["ext_humedad_ambiente"] if "ext_humedad_ambiente" in row.keys() else None,
        "timestamp": _format_ts(row["actualizado_en"]),
    }


def save_module_state(module_id: str, **updates: Any) -> Dict[str, Any]:
    """Actualiza y persiste el estado operativo de un módulo."""
    current = load_module_state(module_id)
    current.update({k: v for k, v in updates.items() if v is not None})
    if updates.get("vpd_kpa") is None and ("air_temperature" in updates or "air_humidity" in updates):
        current["vpd_kpa"] = calculate_vpd(current["air_temperature"], current["air_humidity"])

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if _use_supabase():
        payload = {
            "modulo_id": module_id,
            "temp_ambiente": current["air_temperature"],
            "humedad_ambiente": current["air_humidity"],
            "presion_hpa": current["barometric_pressure_hpa"],
            "nivel_estanque": current["reservoir_level_percent"],
            "dpv_kpa": current["vpd_kpa"],
            "bomba_encendida": bool(current["pump_active"]),
            "servo_angulo": current["vent_servo_angle"],
            "pasos_motor_acumulados": current["stepper_dosing_steps"],
            "humedad_sustrato": current["soil_humidity_pct"],
            "ext_temp_ambiente": current.get("ext_temperature"),
            "ext_humedad_ambiente": current.get("ext_humidity"),
            "actualizado_en": datetime.utcnow().isoformat() + "Z",
        }
        res = _sb_request(
            "POST",
            "estado_modulo",
            params={"on_conflict": "modulo_id"},
            json_body=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        if res is not None:
            return load_module_state(module_id)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO estado_modulo (
                modulo_id, temp_ambiente, humedad_ambiente, presion_hpa,
                nivel_estanque, dpv_kpa, bomba_encendida, servo_angulo,
                pasos_motor_acumulados, humedad_sustrato, ext_temp_ambiente,
                ext_humedad_ambiente, actualizado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                ext_temp_ambiente = excluded.ext_temp_ambiente,
                ext_humedad_ambiente = excluded.ext_humedad_ambiente,
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
                current.get("ext_temperature"),
                current.get("ext_humidity"),
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
    """Guarda una lectura ambiental en telemetria_historica (Supabase Cloud o SQLite respaldo)."""
    computed_vpd = vpd if vpd is not None else calculate_vpd(temp, humidity)
    if _use_supabase():
        payload = {
            "modulo_id": module_id,
            "temp_ambiente": temp,
            "humedad_ambiente": humidity,
            "presion_atmosferica": pressure,
            "dpv_kpa": computed_vpd,
            "nivel_estanque": level,
            "bomba_encendida": bool(pump_active),
            "servo_angulo": servo_angle,
            "pasos_motor_acumulados": steps,
            "origen_dato": origen,
        }
        res = _sb_request("POST", "telemetria_historica", json_body=payload)
        if res is not None:
            return

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
    if _use_supabase():
        payload = {
            "modulo_id": module_id,
            "actuador": target,
            "accion": action,
            "parametro_valor": parameter_value or 0.0,
            "disparado_por": triggered_by,
        }
        res = _sb_request("POST", "registro_comandos", json_body=payload)
        if res is not None:
            return

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


def insert_alert(module_id: str, severity: str, message: str) -> None:
    """Registra una alerta o notificación activa en alertas_sistema (RF2, RF4)."""
    if _use_supabase():
        payload = {
            "modulo_id": module_id,
            "severidad": severity,
            "mensaje": message,
            "leida": False,
        }
        res = _sb_request("POST", "alertas_sistema", json_body=payload)
        if res is not None:
            return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO alertas_sistema (modulo_id, severidad, mensaje, leida)
            VALUES (?, ?, ?, 0)
            """,
            (module_id, severity, message),
        )
        conn.commit()


def get_alerts(module_id: Optional[str] = None, limit: int = 8) -> List[Dict[str, Any]]:
    """Consulta las alertas más recientes registradas para el módulo."""
    if _use_supabase():
        params: Dict[str, Any] = {
            "select": "id,modulo_id,severidad,mensaje,leida,fecha_hora",
            "order": "id.desc",
            "limit": limit,
        }
        if module_id:
            params["modulo_id"] = f"eq.{module_id}"
        rows = _sb_request("GET", "alertas_sistema", params=params)
        if isinstance(rows, list):
            for r in rows:
                r["fecha_hora"] = _format_ts(r.get("fecha_hora"))
            return rows

    with get_connection() as conn:
        if module_id:
            rows = conn.execute(
                """
                SELECT id, modulo_id, severidad, mensaje, leida, fecha_hora
                FROM alertas_sistema
                WHERE modulo_id = ?
                ORDER BY id DESC LIMIT ?
                """,
                (module_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, modulo_id, severidad, mensaje, leida, fecha_hora
                FROM alertas_sistema
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    result = [dict(r) for r in rows]
    for r in result:
        r["fecha_hora"] = _format_ts(r.get("fecha_hora"))
    return result


def get_telemetry_history(limit: int = 10, module_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consulta las últimas lecturas históricas filtradas por módulo (Supabase o SQLite)."""
    if _use_supabase():
        params: Dict[str, Any] = {
            "select": "id,modulo_id,fecha_hora,temp_ambiente,humedad_ambiente,presion_atmosferica,dpv_kpa,nivel_estanque,bomba_encendida,servo_angulo,origen_dato",
            "order": "id.desc",
            "limit": limit,
        }
        if module_id:
            params["modulo_id"] = f"eq.{module_id}"
        rows = _sb_request("GET", "telemetria_historica", params=params)
        if isinstance(rows, list):
            for r in rows:
                r["fecha_hora"] = _format_ts(r.get("fecha_hora"))
                # Normalizamos el booleano de PostgreSQL a 0/1 para mantener compatibilidad con los clientes
                r["bomba_encendida"] = 1 if r.get("bomba_encendida") else 0
            return rows

    with get_connection() as conn:
        if module_id:
            rows = conn.execute(
                """
                SELECT id, modulo_id, fecha_hora, temp_ambiente, humedad_ambiente,
                       presion_atmosferica, dpv_kpa, nivel_estanque, bomba_encendida,
                       servo_angulo, origen_dato
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
                       presion_atmosferica, dpv_kpa, nivel_estanque, bomba_encendida,
                       servo_angulo, origen_dato
                FROM telemetria_historica
                ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    result = [dict(r) for r in rows]
    for r in result:
        r["fecha_hora"] = _format_ts(r.get("fecha_hora"))
    return result
