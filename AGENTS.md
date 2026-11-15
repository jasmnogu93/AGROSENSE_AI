# AGENTS.md — Guía Operativa para Agentes de AgroSense AI (ASAI)

> **Plataforma:** AgroSense AI (ASAI) — Hub de Servicios Agrícolas y Ciberfísicos  
> **Versión:** 3.0 (Optimizada: Comandos, Contratos Intocables, SDD y Plan/Execute vs Swarm)  
> **Ámbito:** Integración de Competencias II (`IEI-094`), IoT (`IEI-059`), Programación Android (`IEI-058`) y Feria de Innovación Santo Tomás.

---

## 1. Propósito y Límites Tri-Servicio (SOA)
El proyecto sigue una Arquitectura Orientada a Servicios (SOA) en un monolito modular con **3 servicios aislados** (nunca mezclar sus reglas):
1. **`AgroFieldService` (`backend/app/routers/field_service.py`, `OrquideasApp/`):** Campos e Invernaderos Tradicionales — Caso Orquídeas (**Integración II `IEI-094`**, RF1–RF7, 80% HR, 18–24 °C, calendario semanal L–D).
2. **`HomeTowerService` (`backend/app/routers/home_tower_service.py`, `firmware/`, `ASAIapp/`):** Mini Torre Hidropónica Domiciliaria (**Feria de Innovación + IoT `IEI-059` + Android `IEI-058`**).
3. **`VerticalFarmService` (`backend/app/routers/vertical_farm_service.py`):** Invernadero Vertical Industrial (escalabilidad comercial y analítica multi-rack).

---

## 2. Comandos Oficiales de Ejecución, Compilación y Pruebas

Usar exactamente estos comandos desde la raíz `C:\Users\Jonathan\Desktop\AGROSENSE_AI` (PowerShell):

* **Ejecutar pruebas automatizadas del Backend (`pytest` sobre BD temporal aislada):**
  ```powershell
  Push-Location backend; .\.venv\Scripts\python.exe -m pytest tests/test_api.py -v; Pop-Location
  ```
* **Levantar Servidor Backend (`FastAPI` + `Uvicorn`; usar `--host 0.0.0.0` si conectan celulares por Wi-Fi):**
  ```powershell
  Push-Location backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000; Pop-Location
  ```
* **Compilar App Android Mini Torre (`ASAIapp/` -> Debug APK):**
  ```powershell
  $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"; Push-Location ASAIapp; .\gradlew.bat assembleDebug --no-daemon; Pop-Location
  ```
* **Compilar App Android Orquídeas (`OrquideasApp/` -> Debug APK):**
  ```powershell
  $env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"; $env:ANDROID_HOME = "C:\Users\Jonathan\AppData\Local\Android\Sdk"; Push-Location OrquideasApp; .\gradlew.bat assembleDebug --no-daemon; Pop-Location
  ```
* **Firmware ESP32 (`firmware/esp32_asai_mqtt/esp32_asai_mqtt.ino`):**
  * Placa en Arduino IDE: `ESP32 Dev Module` (`115200` baudios).
  * Librerías requeridas: `PubSubClient`, `DHT sensor library`, `ESP32Servo`, `Stepper` (`libraries.txt`).

---

## 3. Restricciones Técnicas y Estándares Docentes Intocables

1. **Hardware IoT (`IEI-059` — [`spec-007`](specs/spec-007-esp32-firmware.md)):**
   * **Pinout oficial ESP32 DevKit V1:** DHT11 (`GPIO 4`), BME280 (`I2C SDA 21 / SCL 22`, opcional en hardware), Nivel agua (`GPIO 34` ADC1 + pulso anti-electrólisis de `50 ms` en `GPIO 25`), Relé Bomba (`GPIO 26`), Servo SG90 (`GPIO 18`), Motor PaP ULN2003 (`GPIO 19, 23, 5, 13` — **prohibido usar `GPIO 12`**).
   * **Seguridad física local (Fail-Safe):** Corte inmediato de bomba en `GPIO 26` si el nivel cae `< 20%`, sin depender de internet ni de IA/LLM.
   * **Ciclo no bloqueante:** Usar `millis()` en `loop()` (no `delay(3000)`) para mantener `PubSubClient::loop()` receptivo.
   * **Broker y Tópicos MQTT (`Plaintext`, `QoS 0`):** `tcp://broker.emqx.io:1883`. Telemetría en `ASAI/Temperatura`, `ASAI/Humedad`, `ASAI/Nivel`, `ASAI/DPV`, `ASAI/Presion`, `ASAI/Bomba`, `ASAI/Alerta`; comandos en `ASAI/Bomba/cmd`, `ASAI/Servo/cmd`, `ASAI/Nutrientes/cmd`.
2. **Aplicación Android (`IEI-058` — [`spec-008`](specs/spec-008-android-app.md) / [`spec-009`](specs/spec-009-academic-standards-and-tools.md)):**
   * **Alcance exclusivo:** `ASAIapp/` controla únicamente `HomeTowerService` (la app de Orquídeas para Integración II la desarrolla otro compañero aparte).
   * **Stack docente obligatorio (`Android + mqtt.pdf`):** Java puro (`Empty Views Activity`, `CardView`, `findViewById`, `Intent`), Eclipse Paho (`MqttAsyncClient`), `LocalBroadcastManager` + `BroadcastReceiver` y `tcp://broker.emqx.io:1883` con tópicos `ASAI/*`. **No usar** Kotlin, Jetpack Compose, Retrofit ni arquitecturas no vistas en clase.
3. **Integración de Competencias II (`IEI-094` — [`spec-002`](specs/spec-002-field-greenhouse-service.md)):**
   * Cumplir RF1–RF7 (calendario semanal L–D + hora, perfil 80% HR y 18–24 °C, histórico y notificaciones) con persistencia real en SQLite (`backend/agrosense.db` vía `backend/app/db.py`). Nunca dejar configuraciones críticas solo en RAM.

---

## 4. Protocolo Operativo SDD y Regla de Alineación Previa

Flujo obligatorio para toda feature o cambio estructural:
```text
[1. Especificar en specs/] -> [2. Planificar] -> [3. Log EN PROCESO] -> [4. Implementar] -> [5. Verificar y Log COMPLETADO]
```
* **Consultas y auditorías:** Responder analizando sin modificar ni crear código.
* **Nuevas features o cambios de diseño:** Leer primero el `spec-00X` correspondiente, señalar brechas/riesgos al usuario y esperar confirmación antes de editar código.
* **Trazabilidad:** Actualizar siempre [`specs/PROGRESS_LOGS.md`](specs/PROGRESS_LOGS.md) al cerrar una tarea verificada.

---

## 5. Mapa de Carpetas y Especificaciones (`specs/`)

```text
AGROSENSE_AI/
├── AGENTS.md                              <- Este contrato operativo
├── GUIA_ESTUDIO_Y_MAPA_DEL_SISTEMA.md     <- Mapa de estudio (6 preguntas) y diagnóstico
├── INTEGRACION_EQUIPO_Y_ARQUITECTURA.md   <- Quién hizo qué, herramientas y unificación
├── specs/
│   ├── spec-001-architecture-overview.md   <- SOA, DDL SQLite, contratos Pydantic y DPV Tetens
│   ├── spec-002-field-greenhouse-service.md<- Servicio 1: Orquídeas (IEI-094 RF1-RF7)
│   ├── spec-003-home-tower-service.md      <- Servicio 2: Mini Torre, pines y bloqueo <20%
│   ├── spec-004-vertical-farm-service.md   <- Servicio 3: Invernadero Vertical Industrial
│   ├── spec-005-frontend-adaptive-hub.md   <- Frontend adaptativo (index.html + Tailwind)
│   ├── spec-006-ai-and-simulation.md       <- Motor JEV determinista, simulador y chat DeepSeek
│   ├── spec-007-esp32-firmware.md          <- Firmware ESP32 DevKit V1 + MQTT + Wokwi
│   ├── spec-008-android-app.md             <- App Android ASAIapp (Java + Paho + CardView)
│   ├── spec-009-academic-standards-and-tools.md <- Pautas docentes IEI-058 / IEI-059 / IEI-094
│   └── PROGRESS_LOGS.md                    <- Matriz de estado y bitácora verificada
├── backend/                               <- FastAPI + SQLite (`app/routers/`, `tests/test_api.py`)
├── ASAIapp/                               <- App Android Servicio 2 (Java + Paho MQTT)
├── OrquideasApp/                          <- App Android Servicio 1 (Java + Retrofit HTTP)
└── firmware/                              <- Sketch `.ino`, `diagram.json`, `libraries.txt` y guía ESP32
```

---

## 6. Orquestación de Modelos, Roles y Cuidado de Cuota (`Argon` + `Hydrogen` + `Flash`)

Para aprovechar la doble cuota sin desperdiciar tokens:

1. **Modo 1 — Tareas puntuales o de una sola carpeta (`Plan / Execute` nativo):**
   * Cuando el usuario pida una corrección acotada, editar documentación o un ajuste en una sola carpeta, el agente en `Orchestrator (Argon)` solo investiga lo mínimo necesario, arma el plan y ejecuta **`exit_plan_mode`** para que el **modelo ejecutor rápido** aplique los cambios y corra las pruebas sin gastar la cuota semanal de Argon ni levantar un enjambre innecesario.
2. **Modo 2 — Sprints complejos o trabajo multi-carpeta en paralelo (`swarm`):**
   * Cuando la tarea requiera desarrollar o refactorizar módulos completos en paralelo (ej. `firmware/` + `ASAIapp/` + `backend/`), delegar mediante `swarm{action:"add"}` asignando modelos de la **bolsa diaria** según esta matriz unificada (`workspace: "share"` para autores que editan, `workspace: "inherit"` para verificadores):

| Rol | Dominio / Carpeta Asignada | Modelo Sugerido (`swarm`) |
| :--- | :--- | :--- |
| `architect` / `spec_lead` | Contratos SOA, `specs/`, esquema SQL/Pydantic y `PROGRESS_LOGS.md` | `gemini-4-hydrogen-high` *(o `xhigh` en diseño crítico)* |
| `iot_firmware_engineer` | `firmware/` — ESP32, pulso 50 ms GPIO 25/34, MQTT y fail-safe `<20%` | `gemini-4-hydrogen-high` |
| `android_engineer` | `ASAIapp/` — Java, Paho `MqttAsyncClient`, `LocalBroadcastManager`, `CardView` | `gemini-4-hydrogen-medium` *(o `high` en red/servicios)* |
| `backend_service_dev` | `backend/app/` — FastAPI routers, `db.py`, endpoints REST | `gemini-3.8-flash-high` *(o `hydrogen-medium` en refactors complejos)* |
| `frontend_ui_engineer` | `backend/app/templates/` — UI adaptativa (`index.html`), Tailwind, Fetch | `gemini-3.8-flash-medium` |
| `academic_compliance` | Auditoría contra pautas `IEI-094`, `IEI-059`, `IEI-058` y [`spec-009`](specs/spec-009-academic-standards-and-tools.md) | `gemini-3.8-flash-medium` |
| `qa_verification` | Ejecución real de `pytest`, `gradlew`, verificación de endpoints y bitácora | `gemini-3.8-flash-low` *(o `medium` en E2E)* |

> **Respaldo:** Si un worker en `Hydrogen` agota cuota diaria a mitad de un sprint crítico, usar `swarm{action:"model"}` para moverlo temporalmente a `gemini-4-argon-medium`/`high` explicando el motivo en el tablero (nunca hacer `kill` y `add` para no perder su historial).
