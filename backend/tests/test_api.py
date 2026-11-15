"""
Suite de pruebas automatizadas (pytest) para AgroSense AI (ASAI).
Verifica los 3 servicios SOA, persistencia SQLite aislada en tmp_path,
validaciones RF1-RF7, protección anti-cavitación, simulaciones y UI web.
"""

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Provee un TestClient con base SQLite temporal aislada por cada prueba."""
    test_db_path = str(tmp_path / "test_agrosense.db")
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
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
