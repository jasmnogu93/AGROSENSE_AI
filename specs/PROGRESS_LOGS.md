# PROGRESS_LOGS.md — Historial de Progreso y Trazabilidad SDD (AgroSense AI)

> **Documento:** `specs/PROGRESS_LOGS.md`  
> **Última Actualización:** 2026-11-13 16:57:00 (Chile / Temuco)  
> **Metodología:** Spec-Driven Development (SDD)  
> **Líder de Registro:** `spec_lead` & `academic_compliance`

---

## 1. Matriz de Cumplimiento Global

| Dominio / Servicio | Especificación SDD | Estado General | Cobertura Académica / Proyecto |
| :--- | :--- | :---: | :--- |
| **Arquitectura Tri-Servicio** | `specs/spec-001-architecture-overview.md` | `COMPLETADO` | SOA modular, BD única SQLite (`db.py`), contratos Pydantic y fórmula Tetens |
| **AgroField Service (Orquídeas)** | `specs/spec-002-field-greenhouse-service.md` | `COMPLETADO` | RF1-RF7 implementados con persistencia real en `calendario_semanal` y `estado_modulo` |
| **HomeTower Service (Mini Torres)**| `specs/spec-003-home-tower-service.md` | `COMPLETADO` | Hardware MVP (PaP `19,23,5,13`), anti-cavitación persistente y contratos REST |
| **VerticalFarm Service (Industrial)**| `specs/spec-004-vertical-farm-service.md` | `COMPLETADO` | Visión industrial multi-celda y analítica |
| **Frontend Adaptativo Hub** | `specs/spec-005-frontend-adaptive-hub.md` | `COMPLETADO` | UI adaptativa de 3 pestañas sincronizada en OneDrive, Desktop y GitHub |
| **IA JEV, Chat y Simulación** | `specs/spec-006-ai-and-simulation.md` | `COMPLETADO` | Reglas deterministas, fallback LLM y 4 escenarios de simulación |
| **Firmware ESP32 DevKit V1** | `specs/spec-007-esp32-firmware.md` | `COMPLETADO` | Firmware C++ ESP32 DevKit V1 implementado en `firmware/` con PubSubClient, DHT11 (GPIO 4), pulso anti-electrólisis 50 ms (GPIO 25/34), relé bomba (GPIO 26), servo (GPIO 18), PaP (19, 23, 5, 13), broker `broker.emqx.io:1883`, tópicos `ASAI/*` 1:1 con Android y fail-safe anti-cavitación < 20% |
| **App Móvil Android (IEI-058)** | `specs/spec-008-android-app.md` | `COMPLETADO` | App `ASAIapp/` exclusiva `HomeTowerService` compilada (`app-debug.apk`) con Java + Paho MQTT + `LocalBroadcastManager` + `CardView` |
| **Estándares Académicos y Herramientas** | `specs/spec-009-academic-standards-and-tools.md` | `COMPLETADO` | Compendio compacto IEI-058, IEI-059 (Wokwi/Arduino/MQTTX) e IEI-094 (`CP-01..06`) |

---

## 2. Checklist Detallado por Servicio y Requerimiento

### A. Servicio de Campos e Invernadero Tradicional (`AgroFieldService` — Integración II)
- [x] **RF1 (Calendario de Riego Semanal):** Selector interactivo de días de la semana (`Lun` a `Dom`) y selector de hora fija (`08:00 hrs`). `[COMPLETADO]`
- [x] **RF1 (Persistencia Completa del Calendario en SQLite):** Tabla `calendario_semanal` y capa compartida `db.py` operativas en `backend/agrosense.db`. `[COMPLETADO]`
- [x] **RF2 (Notificación de Riego):** Notificación visual clara en dashboard con día y hora del próximo evento de riego. `[COMPLETADO]`
- [x] **RF3 (Integración Sensores Wi-Fi/Bluetooth):** Ingesta de datos de humedad/temperatura vía HTTP/REST desde ESP32. `[COMPLETADO]`
- [x] **RF4 (Monitoreo Humedad/Temperatura):** Perfil de Orquídeas con umbral óptimo del 80% y rango 18-24 °C. `[COMPLETADO]`
- [x] **RF5 (Registro Histórico):** Tabla de series temporales en SQLite y endpoint de consulta `/api/v1/services/field/history`. `[COMPLETADO]`
- [x] **RF6 (Base de Datos Relacional):** Esquema relacional formal en `database_schema.sql` y base de datos `agrosense.db`. `[COMPLETADO]`
- [x] **RF7 (Visualización en Tiempo Real):** Tarjetas en vivo para humedad relativa, temperatura y alertas en dashboard. `[COMPLETADO]`

### B. Servicio de Mini Torres Domiciliarias (`HomeTowerService` — Feria de Innovación)
- [x] **Especificación Ciberfísica de Hardware:** Mapeo de pines para ESP32 + Arduino Uno (DHT11, BME280, Nivel, Relé, Servo, Stepper). `[COMPLETADO]`
- [x] **Protección contra Cavitación:** Bloqueo inmediato de la mini-bomba sumergible 5V si el nivel de agua cae del 20%. `[COMPLETADO]`
- [x] **Recirculación Continua por Ciclo:** Parámetros de frecuencia (horas) y duración (minutos) de bombeo periódico. `[COMPLETADO]`
- [x] **Control Manual de Actuadores:** Endpoints para accionar Bomba 5V (GPIO 26), Servomotor SG90 (GPIO 18) y PaP 28BYJ-48. `[COMPLETADO]`
- [x] **Cálculo Fisiológico de DPV:** Fórmula de Tetens para Déficit de Presión de Vapor en tiempo real. `[COMPLETADO]`
- [x] **Desarrollo de App Android Nativa (`spec-008`):** Implementada `ASAIapp/` exclusiva para `HomeTowerService` en Java con tarjetas `CardView`, Paho `MqttAsyncClient` + `LocalBroadcastManager` (`broker.emqx.io:1883`) y control de bomba/servo/nutrientes con bloqueo `<20%` (`Android + mqtt.pdf`). `[COMPLETADO]`
- [x] **Desarrollo de Firmware C++ ESP32 (`spec-007`):** Implementado `.ino` en `firmware/esp32_asai_mqtt/esp32_asai_mqtt.ino` con `<PubSubClient.h>`, `<DHT.h>`, `<ESP32Servo.h>`, `<Stepper.h>`, tópicos texto plano `ASAI/*` en `broker.emqx.io:1883` (compatibles 1:1 con `ASAIapp` y MQTTX), pulso 50 ms GPIO 25/34, relé GPIO 26 con corte anti-cavitación `< 20%` y pinout PaP `19, 23, 5, 13` sin GPIO 12. Diagrama Wokwi y guía para Miguel generados. `[COMPLETADO]`
- [x] **Deuda Técnica Backend/Repo:** Sincronizado `main.py` + `index.html`, corregida etiqueta `19, 23, 5, 13`, eliminada BD fantasma y unificada persistencia SQLite en `backend/app/db.py` + `config.py`. `[COMPLETADO]`

### C. Servicio de Invernaderos Verticales Industriales (`VerticalFarmService` — Comercial)
- [x] **Especificación Multi-Celda:** Arquitectura para monitorear racks industriales en paralelo. `[COMPLETADO]`
- [x] **Fallback Ciberfísico Determinista:** Motor de reglas locales si la inferencia en la nube no está disponible. `[COMPLETADO]`
- [x] **Endpoints de Analítica:** Endpoint `/api/v1/services/vertical-farm/overview`. `[COMPLETADO]`

---

## 3. Bitácora de Ejecución (Logs Cronológicos)

| Timestamp | Agente / Rol | Acción Realizada | Resultado / Verificación |
| :--- | :--- | :--- | :--- |
| `2026-11-11 15:56` | `spec_lead` | Creación de `AGENTS.md` con 8 roles especializados y flujo SDD. | Archivo validado en raíz del repositorio. |
| `2026-11-11 15:57` | `architect` | Redacción de `spec-001-architecture-overview.md` con modelo tri-servicio. | Aprobado sin pérdida de información previa. |
| `2026-11-11 15:57` | `academic_compliance`| Redacción de `spec-002-field-greenhouse-service.md` para Orquídeas / Integración II. | Cobertura exacta de RF1 a RF7 de `requerimientos y caso.docx`. |
| `2026-11-11 15:58` | `iot_firmware_engineer`| Redacción de `spec-003-home-tower-service.md` para Mini Torres Domiciliarias. | Detalle de actuadores, pines y cavitación. |
| `2026-11-11 15:58` | `architect` | Redacción de `spec-004-vertical-farm-service.md` y `spec-005-frontend-adaptive-hub.md`. | Diseño UI minimalista y adaptativo. |
| `2026-11-11 15:59` | `spec_lead` | Creación de `PROGRESS_LOGS.md` para trazabilidad continua. | Matriz y checklist activos. |
| `2026-11-11 18:43` | `architect` / `spec_lead` | Actualización de `AGENTS.md` a v2.1: estrategia híbrida (Enjambre `swarm` como eje principal + `invoke_subagent` táctico) y matriz de modelos/esfuerzos (Argon y Flash). | Reglas y propiedad de carpetas listas para ejecución paralela. |
| `2026-11-11 19:13` | `architect` / `spec_lead` | Auditoría y endurecimiento SDD: Regla 3.1 en `AGENTS.md`, SQL/Pydantic en `spec-001..003`, corrección pines PaP (`19,23,5,13`) y creación de `spec-006` (IA/Simulación), `spec-007` (ESP32) y `spec-008` (Android). | Brechas de RAM/BD y desfase `Desktop` vs `OneDrive` documentados sin tocar código. |
| `2026-11-11 19:32` | `backend_service_dev` / `qa_verification` | Creación de `backend/app/db.py`, tablas `calendario_semanal` y `estado_modulo` en SQLite, sincronización `main.py` + `index.html`, corrección etiqueta PaP `19,23,5,13` y limpieza de deuda técnica. | `ALL_BACKEND_CHECKS_PASSED` vía FastAPI `TestClient` (persistencia, bloqueo `<20%` anti-cavitación y los 3 servicios). |
| `2026-11-11 19:43` | `spec_lead` | Creación de `GUIA_ESTUDIO_Y_MAPA_DEL_SISTEMA.md` con método de 6 preguntas, botiquín de diagnóstico código→SDD y glosario sin jerga. | Sincronizado y enlazado desde `ProyectoServiciosASAI/README_PROYECTO_SERVICIOS_ASAI.md`. |
| `2026-11-11 20:04` | `qa_verification` / `architect` | Consolidación en carpeta única limpia `C:\Users\Jonathan\Desktop\AGROSENSE_AI` (fuera de OneDrive), actualización de `.gitignore`, `requirements.txt` (`pytest`, `python-dotenv`) y creación de `backend/tests/test_api.py`. | `pytest -v`: **7 passed** en `1.22s` con BD temporal aislada. |
| `2026-11-12 21:50` | `spec_lead` / `academic_compliance` | Creación de `spec-009-academic-standards-and-tools.md` (compendio IEI-058 Java, IEI-059 Wokwi/Arduino/MQTTX e IEI-094 `CP-01..06`), actualización de `spec-008` a Java, actualización de `AGENTS.md` (Orchestrator Argon + Hydrogen + Flash) y limpieza de PDFs/documentos legado en `AGROSENSE_AI`. | Repositorio depurado con proyecto vigente y `pytest -v` validado. |
| `2026-11-13 00:10` | `spec_lead` / `android_engineer` | Alineación de `spec-007`, `spec-008`, `spec-009`, `AGENTS.md` y `GUIA_ESTUDIO_Y_MAPA_DEL_SISTEMA.md` al estándar `Android + mqtt.pdf` (Java, `CardView`, Eclipse Paho `MqttAsyncClient`, `LocalBroadcastManager`, `broker.emqx.io:1883`, tópicos `ASAI/*` compatibles con MQTTX) y nueva ruta `ASAIapp/`. | Especificaciones y documentación SDD actualizadas; PDF temporal retirado del repo y `pytest` validado. |
| `2026-11-13 00:26` | `android_engineer` / `qa_verification` | Implementación de `ASAIapp/` exclusiva para `HomeTowerService` (`libs.versions.toml`, `app/build.gradle.kts`, `gradle.properties`, `AndroidManifest.xml`, `colors.xml`, 4 íconos vectoriales, `activity_main.xml` con `CardView` + controles manuales, y `MainActivity.java` con `MqttAsyncClient` + `LocalBroadcastManager`). | `.\gradlew.bat assembleDebug --no-daemon`: `BUILD SUCCESSFUL in 1m 24s` (`33 actionable tasks: 33 executed`, `app-debug.apk` generado). |
| `2026-11-13 10:38` | `iot_firmware_engineer` / `qa_verification` | Implementación y verificación de suite de firmware ESP32 DevKit V1 en `firmware/` (`esp32_asai_mqtt.ino`, `libraries.txt`, `diagram.json`, `GUIA_RAPIDA_MIGUEL_ESP32.md`). | Verificación 100% exitosa: pinout exacto (DHT11 GPIO 4, VCC/ADC nivel GPIO 25/34 pulso 50 ms, relé GPIO 26, servo GPIO 18, PaP GPIO 19, 23, 5, 13 sin GPIO 12), broker `broker.emqx.io:1883`, sincronización de tópicos 1:1 con `ASAIapp` y MQTTX, fail-safe anti-cavitación `< 20%` y guía para Miguel. |
| `2026-11-13 10:51` | `spec_lead` / `qa_verification` | Publicación en GitHub (`origin/main`, `origin/MiguelRama`, `origin/JonathanRama`) del paquete completo `ASAIapp/`, `firmware/` y especificaciones SDD actualizadas. | Repositorio sincronizado en GitHub para pruebas de hardware ESP32 + Android por Miguel. |
| `2026-11-13 16:53` | `spec_lead` / `architect` | Optimización de `AGENTS.md` v3.0 (comandos exactos `pytest`/`uvicorn`/`gradlew`, contratos intocables, criterio `Plan/Execute` vs `swarm`), sincronización con kit global `MI_KIT_AGENTES_SDD`, actualización de `GUIA_ESTUDIO_Y_MAPA_DEL_SISTEMA.md` (`firmware/` y `ASAIapp/` implementados) y creación de guía didáctica con plantilla y ejemplos. | Documentación operativa y kit SDD verificados y publicados en GitHub. |
| `2026-11-13 16:57` | `spec_lead` / `qa_verification` | Verificación de colaborador GitHub (`nacomantesmurf` / Marcos Bustos, rol `write`), creación de `GUIA_RAPIDA_MARCOS.md` (foco `AgroFieldService` / Integración II) y publicación de rama `MarcosRama` en GitHub. | Rama `origin/MarcosRama` creada y sincronizada junto a `main`, `MiguelRama` y `JonathanRama`. |
