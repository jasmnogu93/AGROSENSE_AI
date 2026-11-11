# PROGRESS_LOGS.md — Historial de Progreso y Trazabilidad SDD (AgroSense AI)

> **Documento:** `specs/PROGRESS_LOGS.md`  
> **Última Actualización:** 2026-11-11 15:58:00 (Chile / Temuco)  
> **Metodología:** Spec-Driven Development (SDD)  
> **Líder de Registro:** `spec_lead` & `academic_compliance`

---

## 1. Matriz de Cumplimiento Global

| Dominio / Servicio | Especificación SDD | Estado General | Cobertura Académica / Proyecto |
| :--- | :--- | :---: | :--- |
| **Arquitectura Tri-Servicio** | `specs/spec-001-architecture-overview.md` | `COMPLETADO` | SOA desacoplado, modularidad y escalabilidad |
| **AgroField Service (Orquídeas)** | `specs/spec-002-field-greenhouse-service.md` | `COMPLETADO` | 100% de cumplimiento RF1-RF7 Integración II |
| **HomeTower Service (Mini Torres)**| `specs/spec-003-home-tower-service.md` | `COMPLETADO` | Hardware real MVP, Feria Innovación, Android, IoT |
| **VerticalFarm Service (Industrial)**| `specs/spec-004-vertical-farm-service.md` | `COMPLETADO` | Visión industrial multi-celda y computación nube |
| **Frontend Adaptativo Hub** | `specs/spec-005-frontend-adaptive-hub.md` | `COMPLETADO` | UI unificada con selector dinámico de servicios |

---

## 2. Checklist Detallado por Servicio y Requerimiento

### A. Servicio de Campos e Invernadero Tradicional (`AgroFieldService` — Integración II)
- [x] **RF1 (Calendario de Riego Semanal):** Selector interactivo de días de la semana (`Lun` a `Dom`) y selector de hora fija (`08:00 hrs`). `[COMPLETADO]`
- [x] **RF1 (Persistencia en Base de Datos):** Guardado de días y horarios en SQLite al pulsar "Guardar Calendario". `[COMPLETADO]`
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
- [ ] **Desarrollo de App Android Nativa:** Pantallas de conexión y control remoto para el usuario final (En planificación para IEI-058). `[PENDIENTE]`

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
