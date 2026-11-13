# Guía Rápida para Miguel — ESP32 DevKit V1 + MQTT (`AgroSense AI`)

Esta guía te permite cargar el firmware oficial en tu **ESP32 DevKit V1**, cablear la protoboard sin dañar la placa y ejecutar las **3 pruebas en vivo del martes** con **`ASAIapp`** y **`MQTTX`**.

---

## 1. Qué instalar en Arduino IDE (una sola vez)

1. **Soporte de placa ESP32:**
   * En Arduino IDE: `Archivo -> Preferencias -> URLs Adicionales de Gestor de Tarjetas`, agrega:
     `https://espressif.github.io/arduino-esp32/package_esp32_index.json`
   * Ve a `Herramientas -> Placa -> Gestor de Tarjetas`, busca **`esp32`** (por *Espressif Systems*) e instálalo.
   * Selecciona la placa **`DOIT ESP32 DEVKIT V1`** (o `ESP32 Dev Module`).
2. **Librerías necesarias (`Programa -> Incluir Librería -> Administrar Bibliotecas`):**
   * **`PubSubClient`** (por *Nick O'Leary*)
   * **`DHT sensor library`** (por *Adafruit*) — *acepta instalar también `Adafruit Unified Sensor` si te lo pide.*
   * **`ESP32Servo`** (por *Kevin Harrington / John K. Bennett*)
   * *(Nota: `WiFi.h`, `Stepper.h` y `math.h` ya vienen incluidos por defecto en Arduino IDE).*
3. **Monitor Serial:** Configúralo siempre a **`115200 baud`**.

---

## 2. Cómo cablear la Protoboard (Reglas de Oro)

### Regla Crítica: Tierra Común (`GND`) y Fuente de 5V
* **Los sensores** (`DHT11`, `Nivel de agua`, `BME280` opcional) se alimentan con **`3.3V`** del **ESP32**.
* **Los actuadores/motores** (`Relé + Bomba 5V`, `Servo SG90`, `Driver ULN2003 + PaP`) demandan mucha corriente y deben alimentarse desde el pin **`5V` del Arduino Uno R3** (usado solo como fuente de potencia).
* **OBLIGATORIO:** Une con un cable jumper el pin **`GND` del ESP32** al riel **`GND` de la protoboard** y al **`GND` del Arduino Uno**. Sin `GND` común, ni el servo ni el relé ni el motor paso a paso funcionarán.

### Tabla Exacta de Conexiones (Pinout Oficial)

| Componente | Pin del Componente | Conectar a (ESP32 / Fuente) | Nota Importante |
| :--- | :--- | :--- | :--- |
| **DHT11** | `VCC` / `+` | **`3V3`** del ESP32 | Alimentación 3.3V |
| **DHT11** | `DATA` / `OUT` | **`GPIO 4`** del ESP32 | Lectura Temp y Humedad |
| **DHT11** | `GND` / `-` | **`GND`** común | Tierra |
| **Sensor Nivel Resistivo** | `VCC` / `+` | **`GPIO 25`** del ESP32 | **¡No a 3V3 directo!** GPIO 25 lo enciende solo 50 ms para evitar corrosión. |
| **Sensor Nivel Resistivo** | `SIG` / `S` | **`GPIO 34`** del ESP32 | Lectura analógica (0–100%) |
| **Sensor Nivel Resistivo** | `GND` / `-` | **`GND`** común | Tierra |
| **Módulo Relé (Bomba 5V)** | `VCC` | **`5V`** del Arduino Uno | Potencia aislada |
| **Módulo Relé (Bomba 5V)** | `GND` | **`GND`** común | Tierra |
| **Módulo Relé (Bomba 5V)** | `IN` | **`GPIO 26`** del ESP32 | Disparo bomba (cortada si nivel < 20%) |
| **Servomotor SG90** | Rojo (`5V`) | **`5V`** del Arduino Uno | Potencia aislada |
| **Servomotor SG90** | Café/Negro (`GND`) | **`GND`** común | Tierra |
| **Servomotor SG90** | Naranja/Amarillo (`PWM`) | **`GPIO 18`** del ESP32 | Ventilación cenital (`0°` a `90°`) |
| **ULN2003 (Motor PaP)** | `+` / `-` (5–12V) | **`5V` y `GND`** del Arduino Uno | Potencia aislada |
| **ULN2003 (Motor PaP)** | `IN1, IN2, IN3, IN4` | **`GPIO 19, 23, 5, 13`** | **PROHIBIDO usar `GPIO 12`** (bloquea el arranque del ESP32) |
| **BME280 *(opcional)*** | `SDA` / `SCL` | **`GPIO 21` / `GPIO 22`** | Solo si lo conectas y descomentas `#define USAR_BME280` |

---

## 3. Las 2 únicas líneas que debes cambiar antes de subir el código

Abre [`esp32_asai_mqtt/esp32_asai_mqtt.ino`](esp32_asai_mqtt/esp32_asai_mqtt.ino) y edita las líneas **30 y 31**:

```cpp
const char* ssid     = "TU_WIFI";       // <-- Pon el nombre exacto de tu Wi-Fi (2.4 GHz)
const char* password = "TU_PASSWORD";   // <-- Pon la contraseña de tu Wi-Fi
```

> **Tip:** El ESP32 **solo se conecta a redes Wi-Fi de 2.4 GHz** (si compartes internet desde tu celular, activa la banda 2.4 GHz / compatibilidad máxima).  
> **Tip Relé invertido:** Si al iniciar la placa la bomba parte encendida y se apaga al darle `ON`, cambia en las líneas **59–60** `RELAY_ON` a `LOW` y `RELAY_OFF` a `HIGH`.

*Para probar primero en **Wokwi** sin placa física:* usa los archivos de `firmware/esp32_asai_mqtt/` (`esp32_asai_mqtt.ino`, `diagram.json`, `libraries.txt`), cambia `ssid` a `"Wokwi-GUEST"`, `password` a `""` y `#define DHTTYPE DHT22`.

---

## 4. Cómo hacer las 3 Pruebas en Vivo del Martes (`ASAIapp` + `MQTTX`)

Abre **MQTTX** en el computador con esta configuración:
* **Host:** `broker.emqx.io` | **Port:** `1883` | **Protocol:** `mqtt://` | **Plaintext** | **QoS:** `0`
* Suscríbete en MQTTX al comodín **`ASAI/#`** para ver todos los mensajes en vivo.

### Prueba 1: Telemetría en Vivo (ESP32 -> MQTTX -> `ASAIapp`)
1. Conecta el ESP32 y abre el **Monitor Serial (`115200 baud`)**. Verifica `[WiFi] Conectado` y `[MQTT] CONECTADO`.
2. Cada **5 segundos** verás llegar en **MQTTX** y en **`ASAIapp`** los tópicos:
   * `ASAI/Temperatura`, `ASAI/Humedad`, `ASAI/Nivel`, `ASAI/DPV`, `ASAI/Presion`, `ASAI/Bomba`, `ASAI/Alerta`.
3. Acerca el dedo/aliento al `DHT11` y verifica que `Temperatura`, `Humedad` y `DPV` cambian en el celular sin reiniciar la app.

### Prueba 2: Control de Actuadores (`ASAIapp` / MQTTX -> ESP32)
1. Con el sensor de nivel sumergido (**`>= 20%`**):
   * Presiona **Encender Bomba** en `ASAIapp` (o publica `ON` en `ASAI/Bomba/cmd` desde MQTTX).
   * **Resultado esperado:** El relé hace *clic*, la bomba 5V arranca y el ESP32 responde `ON` en `ASAI/Bomba`. Luego presiona **Apagar Bomba** (`OFF`).
2. Presiona **Abrir 90°** y luego **Cerrar 0°** en `ASAIapp` (o publica `90` / `0` en `ASAI/Servo/cmd`).
   * **Resultado esperado:** El servo SG90 gira físicamente a 90° y 0°, y publica el ángulo en `ASAI/Servo`.
3. Presiona **Dosificar (+100)** en `ASAIapp` (o publica `100` en `ASAI/Nutrientes/cmd`).
   * **Resultado esperado:** Los LEDs del ULN2003 parpadean en secuencia, el motor 28BYJ-48 gira 100 pasos y el Monitor Serial confirma `Dosificación de nutrientes completada`.

### Prueba 3: Seguridad Anti-Cavitación (Estanque `< 20%`)
1. Saca el sensor de nivel del agua (o baja el potenciómetro en Wokwi bajo 20%).
2. En el siguiente ciclo (máximo 5 s):
   * **Resultado esperado:** `ASAI/Nivel` baja de `20.00`, `ASAI/Alerta` publica **`ESTANQUE_BAJO`**, la tarjeta en `ASAIapp` se pone **roja** y si intentas encender la bomba (desde `ASAIapp` o enviando `ON` directo desde `MQTTX`), **el ESP32 bloquea el relé físicamente** y mantiene `ASAI/Bomba` en `OFF`.
