# SPEC-004: Servicio de Invernaderos Verticales Industriales (VerticalFarm Service)

> **Documento:** `specs/spec-004-vertical-farm-service.md`  
> **Estado:** APROBADO  
> **Servicio:** `VerticalFarmService` (`/api/v1/services/vertical-farm`)  
> **Ámbito de Cumplimiento:** Visión Comercial a Escala, Feria de Innovación Santo Tomás & Computación en la Nube  
> **Autor:** `architect` & `spec_lead`

---

## 1. Visión y Escalabilidad
El servicio **VerticalFarm** representa la versión empresarial de **AgroSense AI**, diseñada para operar naves industriales agrícolas con decenas o cientos de columnas hidropónicas automatizadas.

### Capacidades Industriales:
* **Monitoreo Multi-Celda:** Agregación de telemetría de múltiples racks/columnas simultáneas.
* **Inferencia Inteligente en la Nube (TypeSafe Jev / LLM Gateway):** Optimización bio-climática basada en algoritmos predictivos que maximizan la tasa fotosintética y minimizan el consumo hídrico y energético.
* **Telemetría Distribución por MQTT:** Soporte para brokers industriales (HiveMQ, Mosquitto, EMQX).

---

## 2. Especificación de Endpoints REST

| Método | Endpoint | Descripción | Payload Request | Respuesta (HTTP 200) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/services/vertical-farm/overview` | Resumen de todas las celdas y racks industriales activos | Ninguno | Lista de celdas, alertas globales, eficiencia hídrica |
| `GET` | `/api/v1/services/vertical-farm/analytics` | Métricas de rendimiento bio-climático y DPV acumulado | Query param `?range=24h` | Curvas de DPV, temperatura y consumo eléctrico |
| `POST` | `/api/v1/services/vertical-farm/optimize` | Solicita optimización global de parámetros mediante IA Jev | `{ "target_metric": "yield_efficiency" }` | Recomendaciones de setpoints |
