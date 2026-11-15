# SPEC-002: Servicio de Campos e Invernaderos Tradicionales (AgroField Service)

> **Documento:** `specs/spec-002-field-greenhouse-service.md`  
> **Estado:** APROBADO  
> **Servicio:** `AgroFieldService` (`/api/v1/services/field`)  
> **Ámbito de Cumplimiento:** Caso Empresa de Orquídeas — Integración de Competencias II (IEI-094)  
> **Autor:** `academic_compliance` & `spec_lead`

---

## 1. Objetivo y Alcance
Proveer la lógica de negocio y endpoints necesarios para cumplir **al 100% los requerimientos funcionales RF1 al RF7** definidos en el documento `requerimientos y caso.docx` de la asignatura *Integración de Competencias II*.

### Parámetros Agronómicos del Caso:
* **Especie:** Orquídeas de Invernadero (*Phalaenopsis sp.*).
* **Punto de ajuste de Humedad Relativa:** Alrededor del **80%** (Rango óptimo: 75% - 85%).
* **Rango de Temperatura:** **18 °C a 24 °C** (noche - día).

---

## 2. Matriz de Requerimientos Funcionales y Criterios de Aceptación

### RF1: Establecer Calendario de Riego
* **Descripción:** El usuario debe poder configurar los días de la semana y las horas para el riego, persistiendo la configuración en la base de datos.
* **Criterios de Aceptación (Gherkin):**
  * **Given** que el usuario accede a la pestaña de Invernadero / Orquídeas.
  * **When** selecciona los días habilitados (ej. `["Lun", "Mié", "Vie"]`), define la hora de riego (ej. `"08:30"`) y pulsa "Guardar Calendario".
  * **Then** la API responde HTTP 200 con el estado actualizado y persiste los datos en SQLite.

### RF2: Notificar Hora de Riego
* **Descripción:** El sistema debe verificar el calendario y enviar una notificación visible/registrada cuando sea momento de regar o indicar la próxima cita de riego.
* **Criterios de Aceptación:**
  * El sistema calcula el próximo día y hora de riego según los días activos.
  * Muestra un componente visual destacado con el mensaje de notificación y un endpoint que emite alertas activas.

### RF3: Integración de Sensores de Humedad
* **Descripción:** Integrar sensores de humedad conectados vía Wi-Fi o Bluetooth.
* **Implementación:** ESP32 DevKit V1 recopilando lecturas de DHT11 y BME280 y transmitiendo a `/api/v1/services/field/telemetry`.

### RF4: Monitorear Nivel de Humedad y Temperatura
* **Descripción:** Monitorear el nivel de humedad ambiental en tiempo real y alertar si está fuera del 80% o fuera de 18-24 °C.
* **Implementación:** Comparación contra los umbrales del perfil de Orquídeas y generación de alertas automáticas si la humedad cae bajo 75% o sube de 85%.

### RF5: Registro Histórico de Condiciones Ambientales
* **Descripción:** Mantener un registro histórico persistente de las condiciones ambientales con frecuencia seleccionable (ej. cada 1 hora).
* **Implementación:** Inserción en la tabla `telemetria_historica` con timestamp y consulta filtrada por límite o fecha.

### RF6: Base de Datos Relacional
* **Descripción:** Almacenamiento persistente estructurado.
* **Implementación:** Tablas SQLite con claves primarias, foráneas e índices temporales.

### RF7: Visualización de Datos en Tiempo Real
* **Descripción:** Visualización gráfica e interactiva de temperatura y humedad en el dashboard web.

---

## 3. Especificación de Endpoints REST

| Método | Endpoint | Descripción | Payload Request | Respuesta (HTTP 200) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/services/field/status` | Estado actual del módulo de orquídeas y telemetría | Ninguno | Estado ambiental, perfil de orquídeas y alertas |
| `GET` | `/api/v1/services/field/schedule` | Obtiene el calendario semanal de riego configurado (RF1) | Ninguno | Días activos, hora programada, próxima notificación |
| `POST` | `/api/v1/services/field/schedule` | Guarda y actualiza días y horas de riego (RF1) | `FieldScheduleUpdate` | Calendario confirmado o HTTP 400 si `active_days` está vacío |
| `GET` | `/api/v1/services/field/notification` | Retorna próxima cita de riego calculada (RF2) | Ninguno | Día, hora, booleano `is_today` y mensaje |
| `POST` | `/api/v1/services/field/telemetry` | Ingesta de lectura de sensores Wi-Fi (RF3, RF4) | `FieldTelemetryInput` | Telemetría registrada en `telemetria_historica` |
| `GET` | `/api/v1/services/field/history` | Consulta histórica filtrada exclusivamente para `invernadero-orquideas` (RF5) | Query param `?limit=10` | Lista de registros cronológicos del módulo de orquídeas |

---

## 4. Contratos JSON Exactos y Reglas de Persistencia
* **`POST /api/v1/services/field/schedule` (`FieldScheduleUpdate`):**
  * **Request:**
    ```json
    {
      "active_days": ["Lun", "Mié", "Vie"],
      "irrigation_time": "08:30",
      "duration_minutes": 20
    }
    ```
  * **Validaciones:** `duration_minutes` entre `1` y `120`; `active_days` no puede estar vacío (HTTP `400`). Valores válidos de días: `["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]`.
  * **Response (`200 OK`):**
    ```json
    {
      "status": "success",
      "message": "Calendario de riego guardado en SQLite con éxito (RF1).",
      "active_days": ["Lun", "Mié", "Vie"],
      "irrigation_time": "08:30",
      "duration_minutes": 20,
      "notification": "🔔 Notificación de Riego (RF2): Próximo riego programado para ..."
    }
    ```
* **`POST /api/v1/services/field/telemetry` (`FieldTelemetryInput`):**
  * **Request:** `{ "air_temperature": 21.4, "air_humidity": 79.8, "soil_humidity_pct": 68.0 }` (`soil_humidity_pct` opcional).
  * **Persistencia:** Tanto el calendario semanal (`calendario_semanal`) como el último estado operativo (`estado_modulo`) y la serie histórica (`telemetria_historica`) persisten en `backend/agrosense.db` mediante `backend/app/db.py`.
