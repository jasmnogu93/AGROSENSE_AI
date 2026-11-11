# SPEC-007: Firmware Embebido ESP32 DevKit V1, MQTT y Fail-Safe (IEI-059)

> **Documento:** `specs/spec-007-esp32-firmware.md`  
> **Estado:** APROBADO PARA IMPLEMENTACIÓN  
> **Carpeta Destino:** `firmware/`  
> **Fuentes Oficiales:** `INVENTARIO_HARDWARE_Y_MAPEO_PINES_MVP.md`, `ESPECIFICACION_DATOS_Y_SERVICIOS_ASAI.md`, `PLAN_DE_DESARROLLO_Y_ENTREGABLES_ASAI.md`  
> **Autor:** `iot_firmware_engineer` & `academic_compliance`

---

## 1. Objetivo y Ámbito Académico
Implementar el firmware C++ (Arduino IDE / PlatformIO) para el microcontrolador **ESP32 DevKit V1** que da vida física tanto al servicio `HomeTowerService` (Feria de Innovación) como a la ingesta Wi-Fi de sensores exigida por **Internet de las Cosas (IEI-059)** e **Integración de Competencias II (RF3, RF4)**.

---

## 2. Arquitectura Eléctrica y Pinout Oficial (Inmutable)

| Dispositivo / Sensor / Actuador | Pin ESP32 DevKit V1 | Alimentación | Regla Crítica de Hardware |
| :--- | :--- | :--- | :--- |
| **Sensor DHT11** | `GPIO 4` (DATA) | `3.3V` ESP32 | Lectura de Temperatura y Humedad Relativa (`<DHT.h>`). |
| **Sensor BME280 / BMP280** | `GPIO 21` (SDA), `GPIO 22` (SCL) | `3.3V` ESP32 | Bus I2C estándar: temperatura precisa y presión barométrica (hPa). |
| **Sensor Nivel Resistivo** | `GPIO 34` (SIG ADC1) + `GPIO 25` (VCC Switch) | `3.3V` conmutado | **Anti-Electrólisis:** `GPIO 25` en `LOW` en reposo; poner `HIGH` solo **50 ms** antes de leer `GPIO 34`, y apagar inmediatamente a `LOW`. |
| **Módulo Relé 1 Canal (Bomba 5V)** | `GPIO 26` (IN) | `5V` Arduino Uno | Aislado de la lógica 3.3V del ESP32; conmuta mini-bomba sumergible 5V. |
| **Micro Servomotor SG90** | `GPIO 18` (PWM) | `5V` Arduino Uno | Control angular `0°` (cerrado) a `90°`/`180°` (ventilación cenital). |
| **Driver ULN2003 (Motor PaP 28BYJ-48)** | **`GPIO 19, 23, 5, 13`** (IN1..IN4) | `5V` Arduino Uno | Dosificación de nutrientes. **Prohibido usar GPIO 12** (strapping pin flash ESP32). |
| **Referencia Eléctrica** | `GND` | Común | **Obligatorio** unir `GND` del ESP32 con `GND` del Arduino Uno R3 (fuente 5V). |

---

## 3. Conectividad, Librerías y Tópicos MQTT

### 3.1. Librerías Requeridas (IEI-059)
* `<WiFi.h>` (conexión WLAN local)
* `<PubSubClient.h>` (cliente MQTT estándar requerido en pauta `DHT11 + MQTT.pdf`)
* `<DHT.h>` (sensor ambiental)
* `<ArduinoJson.h>` / `<HTTPClient.h>` / `<WebServer.h>` (formato JSON, respaldo REST y servidor local)
* `<ESP32Servo.h>` y `<Stepper.h>` (o secuencia de medio paso para ULN2003)
* **Monitor Serial:** `115200 baud` (evidencia obligatoria Semana 14).

### 3.2. Tópicos y Payloads MQTT (Broker HiveMQ / Mosquitto)
* **Publicación de Telemetría (cada `10 segundos`):** `agrosense/telemetria/celda01`
  ```json
  {
    "modulo": "celda-01",
    "temp_ambiente": 22.4,
    "humedad_ambiente": 60.5,
    "presion_hpa": 1014.2,
    "dpv_kpa": 1.05,
    "nivel_estanque": 82.0,
    "bomba_activa": false,
    "servo_angulo": 0
  }
  ```
* **Suscripción de Comandos:** `agrosense/comandos/celda01`
  ```json
  { "actuador": "bomba_agua", "accion": "ON", "parametro": 60, "origen": "android_app" }
  { "actuador": "servo_ventilacion", "accion": "SET_ANGLE", "parametro": 90, "origen": "jev_rules_engine" }
  { "actuador": "motor_nutrientes", "accion": "DISPENSE_STEPS", "parametro": 512, "origen": "manual_dashboard" }
  ```
* **Publicación de Alertas Críticas:** `agrosense/alertas/celda01`

### 3.3. Respaldo HTTP REST y Servidor Local (Pauta Android IEI-058)
* **HTTP POST hacia FastAPI:** Permite enviar lecturas a `/api/v1/telemetry` (y/o `/api/v1/services/field/telemetry`) en formato `TelemetryInput` (`air_temperature`, `air_humidity`, `barometric_pressure_hpa`, `reservoir_level_percent`, `pump_active`, `vent_servo_angle`).
* **Micro-servidor HTTP local en ESP32 (puerto 80):** Exponer `/encender` y `/apagar` para demostración directa desde Android en red local según guía `NodeMCU + Android.pdf`.

---

## 4. Lógica Embebida de Seguridad (*Fail-Safe* Local)
1. Antes de encender o mantener encendido el Relé (`GPIO 26`), el loop verifica el nivel calibrado en `GPIO 34`.
2. **Given** que el nivel cae bajo **20%** (`reservoir_level_percent < 20.0`), **When** llega un comando `ON` por MQTT o HTTP (o la bomba ya estaba encendida), **Then** el ESP32 **corta el relé inmediatamente** en hardware, bloquea la activación y publica alerta en `agrosense/alertas/celda01`.
