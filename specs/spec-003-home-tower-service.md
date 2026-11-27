# SPEC-003: Servicio de Mini Torres Domiciliarias (HomeTower Service)

> **Documento:** `specs/spec-003-home-tower-service.md`  
> **Estado:** APROBADO  
> **Servicio:** `HomeTowerService` (`/api/v1/services/home-tower`)  
> **Ámbito de Cumplimiento:** Proyecto Feria de Innovación Santo Tomás & Programación Android (IEI-058) & IoT (IEI-059)  
> **Autor:** `iot_firmware_engineer` & `android_engineer` & `spec_lead`

---

## 1. Visión y Propuesta de Valor
La **Mini Torre Domiciliaria Inteligente** es un electrodoméstico agrícola para hogares urbanos, permitiendo cultivar alimentos frescos (frutillas, hierbas aromáticas, acelgas, rúcula) de manera 100% automatizada en espacios reducidos.

### Diferenciador de Innovación:
* **Recirculación Continua Programada:** Ciclos periódicos de oxigenación radicular (ej. 15 minutos de bombeo cada 2 horas).
* **Protección Ciberfísica Contra Cavitación:** Apagado inmediato de la mini-bomba sumergible 5V si el sensor resistivo reporta menos del 20% de nivel de agua en el estanque.
* **Control Climático Pasivo y Activo:** Servomotor SG90 que regula la ventilación cenital según el Déficit de Presión de Vapor (DPV) y la temperatura.
* **Dosificación Automatizada de Nutrientes:** Motor paso a paso 28BYJ-48 con driver ULN2003 para suministro preciso de soluciones A y B.
* **Control Nativo desde Android & Web (MQTT Bidireccional):** Conectividad en tiempo real vía `broker.emqx.io:1883` conectando `ESP32` ↔ `ASAIapp` (Android) ↔ `Backend FastAPI / Dashboard Web` (con persistencia en SQLite).

---

## 2. Mapeo Físico de Hardware MVP (Oficial)

> **Regla de Hardware:** Seguir estrictamente `INVENTARIO_HARDWARE_Y_MAPEO_PINES_MVP.md`. El Motor PaP usa **GPIO 19, 23, 5, 13** (se prohíbe GPIO 12 por ser strapping pin de voltaje flash en arranque ESP32).

| Componente | Función en Mini Torre | Pin ESP32 DevKit V1 | Interfaz / Alimentación |
| :--- | :--- | :--- | :--- |
| **DHT11** | Temperatura y Humedad ambiente de la torre | GPIO 4 | 3.3V (VCC / GND) |
| **BME280** | Temperatura precisa, Presión barométrica y Humedad | GPIO 21 (SDA) / GPIO 22 (SCL) | I2C / 3.3V |
| **Sensor Nivel Resistivo** | Medición de agua en estanque con pulso anti-electrólisis | GPIO 34 (ADC1) / GPIO 25 (Excitación 50 ms) | 3.3V |
| **Mini-Bomba 5V** | Recirculación de solución nutritiva por goteo/NFT | GPIO 26 | Relé optoacoplado / 5V Arduino |
| **Servomotor SG90** | Apertura de rejilla de ventilación superior (0° - 90°) | GPIO 18 | PWM (LEDC) / 5V Arduino |
| **Motor PaP 28BYJ-48** | Dispensador peristáltico de nutrientes A/B | **GPIO 19, 23, 5, 13** | Driver ULN2003 / 5V Arduino |

---

## 3. Especificación de Endpoints REST

| Método | Endpoint | Descripción | Payload Request | Respuesta |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/services/home-tower/status` | Estado integral de la torre: nivel estanque, bomba, actuadores, DPV, clima exterior (`DHT11`) y estado del puente MQTT | Ninguno | HTTP 200: telemetría (incl. `exterior_temperature_c`, `exterior_humidity_pct`), actuadores, recirculación, seguridad y `mqtt` |
| `POST` | `/api/v1/services/home-tower/recirculation` | Configura el intervalo y duración del ciclo de bombeo | `RecirculationUpdate` | HTTP 200: parámetros confirmados y `next_cycle_time` |
| `POST` | `/api/v1/services/home-tower/actuators/command` | Comando manual directo a actuador (Bomba, Servo, Motor PaP); persiste en SQLite y publica al tópico MQTT `ASAI/*/cmd` | `ActuatorCommand` | HTTP 200 (`mqtt_published` + log SQLite) o HTTP 400 (bloqueo cavitación) |
| `GET` | `/api/v1/services/home-tower/safety-check` | Evaluación de reglas de protección (cavitación y alivio térmico) | Ninguno | HTTP 200: `NORMAL`, `WARNING`, `CRITICAL` |

---

## 3.1. Puente MQTT Bidireccional en Backend (`backend/app/mqtt_bridge.py`)
* **Broker:** `broker.emqx.io:1883` (`ASAI_MQTT_ENABLED=true` por defecto; desactivable en pruebas unitarias sin red).
* **Suscripción (ESP32 → SQLite/Web):** `ASAI/Temperatura`, `ASAI/Humedad`, `ASAI/Exterior/Temperatura`, `ASAI/Exterior/Humedad`, `ASAI/Nivel`, `ASAI/DPV`, `ASAI/Presion`, `ASAI/Bomba`, `ASAI/Servo`, `ASAI/Alerta` actualizando `estado_modulo` (`celda-01`) y registrando serie temporal en `telemetria_historica`.
* **Publicación (Web REST → ESP32/Android):**
  * `bomba_agua` (`ON`/`OFF`) → `ASAI/Bomba/cmd` (solo si pasa el bloqueo `< 20%`).
  * `servo_ventilacion` (`SET_ANGLE`) → `ASAI/Servo/cmd`.
  * `motor_nutrientes` (`DISPENSE_STEPS`) → `ASAI/Nutrientes/cmd`.

---

## 4. Contratos JSON Exactos y Regla Anti-Cavitación
* **`POST /api/v1/services/home-tower/recirculation` (`RecirculationUpdate`):**
  * **Request:** `{ "interval_hours": 2, "duration_minutes": 15 }` (`interval_hours` `1..24`, `duration_minutes` `1..120`).
* **`POST /api/v1/services/home-tower/actuators/command` (`ActuatorCommand`):**
  * **Request:**
    ```json
    {
      "target": "bomba_agua",
      "action": "ON",
      "parameter_value": 60,
      "triggered_by": "ANDROID_APP"
    }
    ```
  * Valores válidos:
    * `target`: `"bomba_agua" | "servo_ventilacion" | "motor_nutrientes"`
    * `action`: `"ON" | "OFF" | "SET_ANGLE" | "DISPENSE_STEPS"`
  * **Bloqueo Crítico Anti-Cavitación:** Si `target == "bomba_agua"` y `action == "ON"` mientras `reservoir_level_percent < 20.0`, el backend **debe rechazar el comando con HTTP `400`** sin encender la bomba.
* **Compatibilidad Legacy (v1 raíz) y Persistencia Unificada:** Se mantienen activos `/api/v1/telemetry`, `/api/v1/actuators/command`, `/api/v1/schedule` y `/api/v1/health` en `main.py`, compartiendo el módulo `celda-01` en SQLite (`estado_modulo` y `calendario_semanal` vía `backend/app/db.py`) para sincronización inmediata entre simulaciones, web, ESP32 y Android.
