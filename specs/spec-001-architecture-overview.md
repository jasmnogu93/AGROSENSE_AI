# SPEC-001: Visión General de la Arquitectura Tri-Servicio (ASAI)

> **Documento:** `specs/spec-001-architecture-overview.md`  
> **Estado:** APROBADO  
> **Metodología:** Spec-Driven Development (SDD)  
> **Autor:** `architect` & `spec_lead`

---

## 1. Contexto y Justificación del Sistema
La plataforma **AgroSense AI (ASAI)** adopta una **Arquitectura Orientada a Servicios (SOA)** modular diseñada para resolver simultáneamente los requerimientos académicos formales y la propuesta de valor comercial para la Feria de Innovación Santo Tomás.

Para evitar la fricción entre la pauta de un invernadero tradicional de flores y un sistema hidropónico vertical de alta tecnología, el sistema se divide en **tres servicios de dominio independientes**:

```mermaid
graph TD
    UI["🖥️ Frontend Adaptativo Unificado (Dashboard Hub)"] --> Router["FastAPI Core Hub (SOA)"]
    
    subgraph Servicios["Servicios de Dominio ASAI"]
        Router --> S1["🌿 Servicio 1: AgroField Service<br/>(Invernadero Tradicional & Orquídeas)<br/>[Cumplimiento RF1-RF7 IEI-094]"]
        Router --> S2["🏠 Servicio 2: HomeTower Service<br/>(Mini Torres Domiciliarias Urbanas)<br/>[Feria de Innovación & Android IEI-058]"]
        Router --> S3["🏢 Servicio 3: VerticalFarm Service<br/>(Invernaderos Verticales Industriales)<br/>[Escalabilidad Comercial & IA Cloud]"]
    end
    
    S1 --> DB[("💾 Base de Datos Relacional SQLite<br/>(Series Temporales & Auditoría)")]
    S2 --> DB
    S3 --> DB
    
    S1 --> ESP32["🔌 ESP32 DevKit V1<br/>(DHT11 / BME280 / Nivel / Relé / Servo / Stepper)"]
    S2 --> ESP32
```

---

## 2. Definición de los Tres Servicios

| Servicio | Nombre Técnico | Caso de Uso Principal | Tipo de Riego | Parámetros Clave | Evaluación Destino |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Servicio 1** | `AgroFieldService` | Cultivo de Orquídeas en Invernadero / Maceta | **Calendario Semanal** (Días L-D + Horas fijas de riego) | HR óptima ~80%, Temp 18-24 °C | **Integración de Competencias II (IEI-094)** |
| **Servicio 2** | `HomeTowerService` | Mini Torres Hidropónicas Domiciliarias | **Recirculación Continua por Pulsos** (ej. 15 min cada 2h) | Nivel estanque > 20%, DPV, Nutrientes, Ventilación | **Feria de Innovación** & **Android (IEI-058)** |
| **Servicio 3** | `VerticalFarmService` | Granjas Verticales Comerciales Multi-Torre | Recirculación Hidrodinámica Multi-Nivel | DPV industrial, balance electroquímico, inferencia IA | **Escalabilidad y Visión Empresarial** |

---

## 3. Contratos de Datos y Esquema Compartido (Shared Kernel)
Todos los servicios comparten:
1. **Base de Datos Relacional SQLite (`agrosense.db`):**
   * `modulos_hidroponicos`: Registro de unidades de hardware activas.
   * `perfiles_cultivo`: Parámetros agronómicos (Orquídeas, Frutillas, Hortalizas).
   * `telemetria_historica`: Registro cronológico persistente de sensores ambientales.
   * `registro_comandos`: Auditoría polimórfica de actuadores (Relé, Servo, Stepper).
   * `calendario_semanal`: Almacenamiento de días activos y horarios de riego (RF1).
2. **Protocolos de Comunicación:**
   * Endpoints REST (HTTP/1.1 con JSON UTF-8).
   * Documentación OpenAPI autogenerada en `/docs`.
   * Payloads tipados mediante esquemas Pydantic v2.
