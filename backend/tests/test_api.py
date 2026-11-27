"""
Suite de pruebas automatizadas (pytest) para AgroSense AI (ASAI).
Verifica los 3 servicios SOA, persistencia SQLite aislada en tmp_path,
validaciones RF1-RF7, protección anti-cavitación, simulaciones y UI web.
"""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.config import settings
from app.main import app
from app.mqtt_bridge import mqtt_bridge


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Provee un TestClient con base SQLite temporal aislada por cada prueba."""
    test_db_path = str(tmp_path / "test_agrosense.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    monkeypatch.setattr(settings, "MQTT_ENABLED", False)
    db.init_db()
    with TestClient(app) as test_client:
        yield test_client


def test_dashboard_renders_tri_service_ui_and_official_pinout(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "tab-field" in res.text
    assert "tab-home-tower" in res.text
    assert "tab-vertical-farm" in res.text
    assert "GPIO 19, 23, 5, 13" in res.text
    assert "GPIO 19, 13, 12, 14" not in res.text


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_field_schedule_validation_and_persistence(client):
    # Rechaza lista de días vacía (HTTP 400)
    bad = client.post(
        "/api/v1/services/field/schedule",
        json={"active_days": [], "irrigation_time": "08:30", "duration_minutes": 20},
    )
    assert bad.status_code == 400

    # Rechaza día inválido (HTTP 400)
    bad_day = client.post(
        "/api/v1/services/field/schedule",
        json={"active_days": ["Funday"], "irrigation_time": "08:30", "duration_minutes": 20},
    )
    assert bad_day.status_code == 400

    # Guarda días válidos y valida persistencia directa en SQLite
    ok = client.post(
        "/api/v1/services/field/schedule",
        json={"active_days": ["Mar", "Jue", "Sáb"], "irrigation_time": "07:15", "duration_minutes": 25},
    )
    assert ok.status_code == 200
    persisted = db.load_schedule("invernadero-orquideas")
    assert persisted["active_days"] == ["Mar", "Jue", "Sáb"]
    assert persisted["irrigation_time"] == "07:15"
    assert persisted["duration_minutes"] == 25


def test_field_telemetry_ingestion_and_history(client):
    # Simular un evento en la Mini Torre (celda-01) para comprobar aislamiento de historial
    assert client.post("/api/v1/simulate/optimo").status_code == 200

    post_res = client.post(
        "/api/v1/services/field/telemetry",
        json={"air_temperature": 21.2, "air_humidity": 80.5, "soil_humidity_pct": 71.0},
    )
    assert post_res.status_code == 200
    status_res = client.get("/api/v1/services/field/status")
    assert status_res.status_code == 200
    assert status_res.json()["telemetry"]["air_humidity"] == 80.5
    assert status_res.json()["active_alerts"] == []

    hist_res = client.get("/api/v1/services/field/history?limit=10")
    assert hist_res.status_code == 200
    body = hist_res.json()
    assert body["total_records"] >= 1
    assert all(r["modulo_id"] == "invernadero-orquideas" for r in body["history"])


def test_home_tower_anti_cavitation_blocks_pump_under_20_percent(client):
    # Simular estanque vacío (12% < 20%)
    sim = client.post("/api/v1/simulate/estanque_vacio")
    assert sim.status_code == 200
    assert sim.json()["jev_decision"]["risk_level"] == "CRITICAL"

    # Intentar encender bomba debe retornar HTTP 400
    blocked = client.post(
        "/api/v1/services/home-tower/actuators/command",
        json={"target": "bomba_agua", "action": "ON", "parameter_value": 60, "triggered_by": "PYTEST"},
    )
    assert blocked.status_code == 400
    assert "RECHAZADO" in blocked.json()["detail"]

    safety = client.get("/api/v1/services/home-tower/safety-check")
    assert safety.status_code == 200
    assert safety.json()["risk_level"] == "CRITICAL"


def test_home_tower_actuators_and_recirculation_sync_with_main_telemetry(client):
    assert client.post("/api/v1/simulate/optimo").status_code == 200

    cmd_on = client.post(
        "/api/v1/services/home-tower/actuators/command",
        json={"target": "bomba_agua", "action": "ON", "parameter_value": 60, "triggered_by": "PYTEST"},
    )
    assert cmd_on.status_code == 200
    assert cmd_on.json()["pump_active"] is True

    # Verificar consistencia entre HomeTower y /api/v1/telemetry/latest
    assert client.get("/api/v1/services/home-tower/status").json()["actuators"]["pump_active"] is True
    assert client.get("/api/v1/telemetry/latest").json()["pump_active"] is True

    # Recirculación persistente
    recirc = client.post(
        "/api/v1/services/home-tower/recirculation",
        json={"interval_hours": 3, "duration_minutes": 10},
    )
    assert recirc.status_code == 200
    assert db.load_schedule("celda-01")["interval_hours"] == 3


def test_vertical_farm_and_chat_endpoints(client):
    assert client.get("/api/v1/services/vertical-farm/overview").status_code == 200
    assert client.get("/api/v1/services/vertical-farm/analytics").status_code == 200
    assert client.post("/api/v1/services/vertical-farm/optimize", json={"target_metric": "yield_efficiency"}).status_code == 200

    chat = client.post("/api/v1/chat/farm", json={"question": "¿Cómo está el nivel del estanque y la bomba?"})
    assert chat.status_code == 200
    assert "estanque" in chat.json()["answer"].lower()


def test_home_tower_mqtt_bridge_ingestion(client):
    """Verifica ingesta de telemetría IoT vía mqtt_bridge.handle_message y reflejo en /status."""
    mqtt_bridge.handle_message("ASAI/Temperatura", "23.4")
    mqtt_bridge.handle_message("ASAI/Humedad", "68.2")
    mqtt_bridge.handle_message("ASAI/Exterior/Temperatura", "19.5")
    mqtt_bridge.handle_message("ASAI/Exterior/Humedad", "55.0")
    mqtt_bridge.handle_message("ASAI/Nivel", "77.5")
    mqtt_bridge.handle_message("ASAI/Presion", "1015.0")
    mqtt_bridge.handle_message("ASAI/DPV", "0.88")
    mqtt_bridge.handle_message("ASAI/Bomba", "ON")
    mqtt_bridge.handle_message("ASAI/Servo", "45")
    mqtt_bridge.handle_message("ASAI/Alerta", "ALERTA_TEST_BOMBA")

    # Payload inválido no debe romper ni alterar estado
    mqtt_bridge.handle_message("ASAI/Temperatura", "INVALID_FLOAT")

    res = client.get("/api/v1/services/home-tower/status")
    assert res.status_code == 200
    body = res.json()
    tel = body["telemetry"]
    act = body["actuators"]
    mqtt_stat = body["mqtt"]

    assert tel["temperature_c"] == 23.4
    assert tel["humidity_pct"] == 68.2
    assert tel["exterior_temperature_c"] == 19.5
    assert tel["exterior_humidity_pct"] == 55.0
    assert tel["reservoir_level_pct"] == 77.5
    assert tel["pressure_hpa"] == 1015.0
    assert tel["dpv_kpa"] == 0.88
    assert act["pump_active"] is True
    assert act["vent_servo_angle"] == 45
    assert mqtt_stat["last_alert"] == "ALERTA_TEST_BOMBA"
    assert mqtt_stat["last_message_at"] is not None
    assert mqtt_stat["enabled"] is False


def test_home_tower_actuator_command_mqtt_dispatch_and_cavitation_block(client, monkeypatch):
    """Verifica publicación MQTT de comandos y bloqueo por cavitación (<20%) sin publicar."""
    # Estado óptimo (nivel 85%)
    assert client.post("/api/v1/simulate/optimo").status_code == 200

    published_calls = []

    def fake_publish(target: str, action: str, parameter_value=None):
        published_calls.append((target, action, parameter_value))
        return True

    monkeypatch.setattr(mqtt_bridge, "publish_actuator_command", fake_publish)

    # 1. Comando exitoso -> debe publicar en MQTT
    res = client.post(
        "/api/v1/services/home-tower/actuators/command",
        json={"target": "bomba_agua", "action": "ON", "parameter_value": 60.0, "triggered_by": "TEST_UNIT"},
    )
    assert res.status_code == 200
    assert res.json()["mqtt_published"] is True
    assert len(published_calls) == 1
    assert published_calls[0] == ("bomba_agua", "ON", 60.0)

    # 2. Comando bloqueado por nivel crítico (<20%) -> NO debe publicar en MQTT
    assert client.post("/api/v1/simulate/estanque_vacio").status_code == 200
    published_calls.clear()

    blocked = client.post(
        "/api/v1/services/home-tower/actuators/command",
        json={"target": "bomba_agua", "action": "ON", "parameter_value": 60.0, "triggered_by": "TEST_UNIT"},
    )
    assert blocked.status_code == 400
    assert len(published_calls) == 0

    # 3. Comando a servo -> debe publicar en MQTT
    servo_res = client.post(
        "/api/v1/services/home-tower/actuators/command",
        json={"target": "servo_ventilacion", "action": "SET_ANGLE", "parameter_value": 90.0, "triggered_by": "TEST_UNIT"},
    )
    assert servo_res.status_code == 200
    assert servo_res.json()["mqtt_published"] is True
    assert len(published_calls) == 1
    assert published_calls[0] == ("servo_ventilacion", "SET_ANGLE", 90.0)


def test_field_orchid_alerts_rf4_and_notification_trigger_rf2(client):
    """Verifica alertas RF4 (<75%, >85%, fuera 18-24°C) y notificación activa RF2."""
    res_bad = client.post(
        "/api/v1/services/field/telemetry",
        json={"air_temperature": 27.5, "air_humidity": 60.0, "soil_humidity_pct": 50.0, "barometric_pressure_hpa": 1012.5},
    )
    assert res_bad.status_code == 200
    body_bad = res_bad.json()
    assert body_bad["telemetry"]["status"] == "ALERTA"
    assert len(body_bad["active_alerts"]) == 2
    assert any("HUMEDAD BAJA" in a for a in body_bad["active_alerts"])
    assert any("TÉRMICA" in a for a in body_bad["active_alerts"])

    # Verificar que también persiste en alertas_sistema y refleja en /status
    status_res = client.get("/api/v1/services/field/status")
    assert status_res.status_code == 200
    st = status_res.json()
    assert len(st["active_alerts"]) == 2
    assert len(st["alerts_log"]) >= 2

    # Disparar notificación RF2
    notif = client.post("/api/v1/services/field/notification/trigger")
    assert notif.status_code == 200
    assert notif.json()["is_due_now"] is True
    assert "Hora de Riego" in notif.json()["notification_message"]


def test_field_sensor_connection_rf3_and_frequency_rf5_and_chart_rf7(client):
    """Verifica Conectar Sensores RF3 (éxito y fallo), frecuencia RF5 y gráfico RF7 en HTML."""
    # Conexión exitosa Wi-Fi
    ok_conn = client.post(
        "/api/v1/services/field/sensors/connect",
        json={"protocol": "Wi-Fi", "device_id": "ESP32-Wokwi-Test", "simulate_failure": False},
    )
    assert ok_conn.status_code == 200
    assert ok_conn.json()["connected"] is True

    # Fallo simulado Bluetooth -> entrega pasos de solución
    fail_conn = client.post(
        "/api/v1/services/field/sensors/connect",
        json={"protocol": "Bluetooth", "device_id": "HC05-Orq", "simulate_failure": True},
    )
    assert fail_conn.status_code == 200
    assert fail_conn.json()["connected"] is False
    assert len(fail_conn.json()["troubleshooting"]) >= 3

    # Frecuencia de historial RF5
    freq_res = client.post(
        "/api/v1/services/field/history/frequency",
        json={"recording_frequency_minutes": 15},
    )
    assert freq_res.status_code == 200
    assert freq_res.json()["recording_frequency_minutes"] == 15
    assert client.get("/api/v1/services/field/history").json()["recording_frequency_minutes"] == 15

    # UI contiene los componentes RF3 y RF7
    dash = client.get("/")
    assert dash.status_code == 200
    assert "fieldRealtimeChart" in dash.text
    assert "Conectar Sensores (RF3)" in dash.text


def test_supabase_rest_adapter_roundtrip_mocked(client, monkeypatch):
    """Verifica el adaptador REST de Supabase (RF6) sin depender de red externa en pytest."""
    calls = []

    def fake_sb_request(method, table, *, params=None, json_body=None, prefer=None):
        calls.append((method, table, params, json_body))
        if table == "modulos_hidroponicos":
            return [{"id": "invernadero-orquideas"}]
        if table == "calendario_semanal" and method == "GET":
            return [{
                "modulo_id": "invernadero-orquideas",
                "dias_activos_json": '["Lun", "Jue"]',
                "hora_riego": "09:00",
                "duracion_minutos": 15,
                "intervalo_horas": 24,
                "frecuencia_registro_min": 30,
            }]
        if table == "telemetria_historica" and method == "GET":
            return [{
                "id": 99,
                "modulo_id": "invernadero-orquideas",
                "fecha_hora": "2026-11-22T14:00:00+00:00",
                "temp_ambiente": 21.5,
                "humedad_ambiente": 80.1,
                "presion_atmosferica": 1013.2,
                "dpv_kpa": 0.51,
                "nivel_estanque": 100.0,
                "bomba_encendida": False,
                "servo_angulo": 0,
                "origen_dato": "SUPABASE_TEST",
            }]
        return []

    monkeypatch.setattr(settings, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_KEY", "sb_secret_test")
    monkeypatch.setattr(db, "_ALLOW_SUPABASE_FOR_TEST", True)
    monkeypatch.setattr(db, "_supabase_schema_missing", False)
    monkeypatch.setattr(db, "_sb_request", fake_sb_request)

    info = db.get_storage_backend_info()
    assert info["cloud"] is True
    assert info["label"] == "Supabase Cloud"

    sched = db.load_schedule("invernadero-orquideas")
    assert sched["active_days"] == ["Lun", "Jue"]
    assert sched["recording_frequency_minutes"] == 30

    hist = db.get_telemetry_history(limit=5, module_id="invernadero-orquideas")
    assert len(hist) == 1
    assert hist[0]["origen_dato"] == "SUPABASE_TEST"
    assert any(c[0] == "GET" and c[1] == "telemetria_historica" for c in calls)


def test_field_wokwi_pump_and_demo_cycle(client, monkeypatch):
    """Verifica control manual de aspersión (Pin 5) y ciclo automático demo 10s/5s."""
    pump_calls = []

    def fake_field_pump(turn_on: bool) -> bool:
        pump_calls.append(turn_on)
        return True

    monkeypatch.setattr(mqtt_bridge, "publish_field_pump", fake_field_pump)

    # 1. Encendido y apagado manual
    on_res = client.post("/api/v1/services/field/pump", json={"action": "ON"})
    assert on_res.status_code == 200
    assert on_res.json()["pump_active"] is True
    assert on_res.json()["mqtt_published"] is True

    off_res = client.post("/api/v1/services/field/pump", json={"action": "OFF"})
    assert off_res.status_code == 200
    assert off_res.json()["pump_active"] is False

    # 2. Ciclo demo inválido (intervalo <= duración) debe dar 400
    bad_demo = client.post("/api/v1/services/field/demo-cycle", json={"enabled": True, "interval_seconds": 5, "duration_seconds": 5})
    assert bad_demo.status_code == 400

    # 3. Ciclo demo válido 10s / 5s -> enciende de inmediato y luego detiene limpio
    ok_demo = client.post("/api/v1/services/field/demo-cycle", json={"enabled": True, "interval_seconds": 10, "duration_seconds": 5})
    assert ok_demo.status_code == 200
    assert ok_demo.json()["irrigation_control"]["demo_enabled"] is True
    assert ok_demo.json()["irrigation_control"]["pump_active"] is True

    stop_demo = client.post("/api/v1/services/field/demo-cycle", json={"enabled": False, "interval_seconds": 10, "duration_seconds": 5})
    assert stop_demo.status_code == 200
    assert stop_demo.json()["irrigation_control"]["demo_enabled"] is False
    assert stop_demo.json()["irrigation_control"]["pump_active"] is False
    assert pump_calls == [True, False, True, False]


