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
* **Control Nativo desde Android:** Conectividad y control remoto desde smartphone.

---

## 2. Mapeo Físico de Hardware MVP

| Componente | Función en Mini Torre | Pin ESP32 DevKit V1 | Interfaz / Alimentación |
| :--- | :--- | :--- | :--- |
| **DHT11** | Temperatura y Humedad ambiente de la torre | GPIO 4 | 3.3V (VCC / GND) |
| **BME280** | Temperatura precisa, Presión barométrica y Humedad | GPIO 21 (SDA) / GPIO 22 (SCL) | I2C / 3.3V |
| **Sensor Nivel Resistivo** | Medición de agua en estanque con pulso anti-electrólisis | GPIO 34 (ADC1) / GPIO 25 (Excitación 50 ms) | 3.3V |
| **Mini-Bomba 5V** | Recirculación de solución nutritiva por goteo/NFT | GPIO 26 | Relé optoacoplado / 5V Arduino |
| **Servomotor SG90** | Apertura de rejilla de ventilación superior (0° - 90°) | GPIO 18 | PWM (LEDC) / 5V Arduino |
| **Motor PaP 28BYJ-48** | Dispensador peristáltico de nutrientes A/B | GPIO 19, 13, 12, 14 | Driver ULN2003 / 5V Arduino |

---

## 3. Especificación de Endpoints REST

| Método | Endpoint | Descripción | Payload Request | Respuesta (HTTP 200) |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/services/home-tower/status` | Estado integral de la torre: nivel estanque, bomba, actuadores y DPV | Ninguno | Telemetría, seguridad de bomba, salud del sistema |
| `POST` | `/api/v1/services/home-tower/recirculation` | Configura el intervalo y duración del ciclo de bombeo | `{ "interval_hours": 2, "duration_minutes": 15 }` | Parámetros confirmados |
| `POST` | `/api/v1/services/home-tower/actuators/command` | Comando manual directo a actuador (Bomba, Servo, Motor PaP) | `{ "actuator": "bomba_agua", "action": "ON", "parameter_value": 60 }` | Resultado del comando y log en BD |
| `GET` | `/api/v1/services/home-tower/safety-check` | Evaluación de reglas de protección (cavitación y alivio térmico) | Ninguno | Estado de riesgo (`NORMAL`, `WARNING`, `CRITICAL`) |
