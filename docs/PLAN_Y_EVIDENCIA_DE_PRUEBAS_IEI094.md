# Plan y Evidencia de Pruebas de Funcionamiento — Integración de Competencias II (`IEI-094`)

> **Proyecto:** AgroSense AI (`AgroFieldService` — Invernadero de Orquídeas)  
> **Criterio Evaluado (`CE5N2`):** *Construye Pruebas de funcionamiento: diseñando casos de prueba, ejecutando, documentando y validando el funcionamiento del sistema.*  
> **Suite Automatizada:** [`backend/tests/test_api.py`](../backend/tests/test_api.py) (`pytest tests/test_api.py -v`)  
> **Base de Datos:** Supabase PostgreSQL (`database_schema_supabase.sql`) + Respaldo SQLite (`agrosense.db`)

---

## 1. Matriz Formal de Casos de Prueba (`CP-ORQ-01` a `CP-ORQ-08`)

| ID | Requerimiento | Condición Inicial | Entrada / Evento | Resultado Esperado | Resultado Obtenido y Evidencia | Estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **`CP-ORQ-01`** | **RF1:** Calendario semanal de riego | Usuario en pestaña *Invernadero & Orquídeas* (`/`) | Selecciona `["Mar", "Jue", "Sáb"]`, hora `"07:15"`, `25 min`, guarda vía `POST /api/v1/services/field/schedule` | HTTP `200`, persistencia en `calendario_semanal`; rechazo HTTP `400` si lista vacía o día inválido | `test_field_schedule_validation_and_persistence`: `400` en día inválido/vacío y `200` persistiendo `["Mar", "Jue", "Sáb"]` | `APROBADO` |
| **`CP-ORQ-02`** | **RF2:** Notificar hora de riego | Calendario activo configurado | Consultar `/notification` o activar `POST /api/v1/services/field/notification/trigger` | Mensaje destacado con día/hora y registro en tabla `alertas_sistema` | `test_field_orchid_alerts_rf4_and_notification_trigger_rf2`: retorna `is_due_now: true` y registra alerta | `APROBADO` |
| **`CP-ORQ-03`** | **RF3:** Emparejar sensores (caso éxito) | Panel *Conectar Sensores* abierto | `POST /api/v1/services/field/sensors/connect` (`protocol="Wi-Fi"`, `simulate_failure=false`) | Verifica conexión y confirma estado `connected: true` | `test_field_sensor_connection_rf3_and_frequency_rf5_and_chart_rf7`: responde `connected: true` y audita en BD | `APROBADO` |
| **`CP-ORQ-04`** | **RF3 (Excepción):** Fallo de conexión de sensor | Panel *Conectar Sensores* abierto | `POST /api/v1/services/field/sensors/connect` (`protocol="Bluetooth"`, `simulate_failure=true`) | Estado `connected: false` + lista de instrucciones paso a paso de solución y alerta registrada | Devuelve `troubleshooting` con 4 pasos específicos y registra evento en `alertas_sistema` | `APROBADO` |
| **`CP-ORQ-05`** | **RF4:** Monitoreo y alerta fuera del `80%` / `18–24 °C` | Sensor enviando lecturas por Wi-Fi/Wokwi | `POST /api/v1/services/field/telemetry` con `27.5 °C` y `60.0 %` HR | Clasifica `status: "ALERTA"`, genera `ALERTA HUMEDAD BAJA` y `ALERTA TÉRMICA` y las persiste en BD | `test_field_orchid_alerts_rf4_and_notification_trigger_rf2`: 2 alertas generadas, guardadas en `alertas_sistema` y visibles en `/status` | `APROBADO` |
| **`CP-ORQ-06`** | **RF5:** Histórico filtrado y frecuencia seleccionable | Datos de Mini Torre y Orquídeas coexistiendo | `POST /api/v1/services/field/history/frequency` (`15 min`) y `GET /api/v1/services/field/history` | Persiste `recording_frequency_minutes = 15` y retorna solo filas con `modulo_id = "invernadero-orquideas"` | `test_field_telemetry_ingestion_and_history` + `...frequency_rf5...`: aislamiento 100% verificado | `APROBADO` |
| **`CP-ORQ-07`** | **RF6:** Conexión a Base de Datos Supabase | Variables `SUPABASE_URL` / `SUPABASE_KEY` activas | Llamadas a `get_storage_backend_info()`, `load_schedule()` y `get_telemetry_history()` | Adaptador PostgREST autentica con `apikey`, lee/escribe tablas `public.*` y reporta `Supabase Cloud` | `test_supabase_rest_adapter_roundtrip_mocked`: `cloud: True`, `label: "Supabase Cloud"`, consulta `telemetria_historica` validada | `APROBADO` |
| **`CP-ORQ-08`** | **RF7:** Visualización en tiempo real (`Chart.js`) | Usuario viendo pestaña *Invernadero & Orquídeas* | `GET /` y polling automático `refreshFieldStatus()` cada 5 s | Renderiza `fieldRealtimeChart`, métricas en vivo y opción `Conectar Sensores (RF3)` sin recargar | `test_field_sensor_connection_rf3_and_frequency_rf5_and_chart_rf7`: `HTTP 200`, `fieldRealtimeChart` y controles presentes | `APROBADO` |
| **`CP-ORQ-09`** | **RF1/Wokwi:** Control manual Pin 5 y Ciclo Demo (`10s / 5s`) | Wokwi ESP32 conectado a `broker.emqx.io` | `POST /api/v1/services/field/pump` y `POST /api/v1/services/field/demo-cycle` (`10s/5s`) | Enciende relé Wokwi (`ASAI/Orquideas/Bomba/cmd`), apaga tras 5 s y rechaza `interval <= duration` (`HTTP 400`) | `test_field_wokwi_pump_and_demo_cycle`: `[True, False, True, False]` verificado y validación `400` aprobada | `APROBADO` |

---

## 2. Registro de Ejecución de Pruebas Automatizadas (`pytest`)

Comando oficial ejecutado en `c:\Users\Jonathan\Desktop\AGROSENSE_AI`:

```powershell
Push-Location backend; .\.venv\Scripts\python.exe -m pytest tests/test_api.py -v; Pop-Location
```

Resultado verificado (`2026-11-22`):
* **Total recolectado:** `13` pruebas automatizadas (`9` previas de plataforma SOA + `4` específicas para `IEI-094`, Wokwi y adaptador `Supabase`).
* **Resultado:** **`13 passed in 4.21s`** (`0 failed`, `0 skipped`).
