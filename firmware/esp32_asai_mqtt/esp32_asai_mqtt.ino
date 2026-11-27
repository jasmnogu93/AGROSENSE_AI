/*
 * ============================================================================
 *  AGROSENSE AI (ASAI) - Firmware Oficial ESP32 DevKit V1 + MQTT
 *  Servicio: HomeTowerService (Mini Torre Hidropónica Doméstica)
 *  Asignatura: Internet de las Cosas (IEI-059) & Feria de Innovación
 * ============================================================================
 *
 *  GUÍA RÁPIDA DE CONFIGURACIÓN PARA MIGUEL (1 MINUTO):
 *  1. Cambia las líneas "TU_WIFI" y "TU_PASSWORD" justo aquí abajo (red 2.4 GHz).
 *  2. Si tu módulo relé enciende al revés (activo en LOW), cambia RELAY_ON / RELAY_OFF.
 *  3. Abre el Monitor Serial a 115200 baudios para ver lecturas y comandos.
 *  4. Broker MQTT: broker.emqx.io (puerto 1883, sin usuario ni contraseña).
 *
 *  NOTA PARA SIMULACIÓN EN WOKWI:
 *  Wokwi solo trae DHT22 (sensor blanco). Si pruebas en Wokwi, cambia DHT11 por DHT22.
 *  En tu placa física real, déjalo en DHT11.
 * ============================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ESP32Servo.h>
#include <Stepper.h>
#include <math.h>

// ============================================================================
// 1. CONFIGURACIÓN WI-FI Y MQTT (¡EDITA ESTAS 2 LÍNEAS!)
// ============================================================================
const char* ssid     = "TU_WIFI_2_4GHZ";     // <-- Nombre de tu Wi-Fi (debe ser 2.4 GHz)
const char* password = "TU_PASSWORD_WIFI";   // <-- Contraseña de tu Wi-Fi

// -- Aqui se configura el broker MQTT (broker.emqx.io), puerto 1883 y el ID unico del ESP32 --
const char* mqtt_server    = "broker.emqx.io";
const int   mqtt_port      = 1883;
const char* mqtt_client_id = "ESP32_ASAI_01";

// ============================================================================
// 2. PINOUT OFICIAL INMUTABLE (SPEC-007 / INVENTARIO HARDWARE MVP)
// ============================================================================
// Sensor ambiental DHT11 (alimentado a 3.3V desde ESP32)
#define DHTPIN   4
#define DHTTYPE  DHT11   // Cambiar a DHT22 solo si simulas en Wokwi

// Sensor de nivel de agua resistivo con protección anti-electrólisis
const int LEVEL_VCC_PIN = 25; // GPIO 25: en LOW en reposo; HIGH solo 50 ms al leer
const int LEVEL_ADC_PIN = 34; // GPIO 34: entrada analógica ADC1 (0..4095)

// Calibración del sensor de nivel (ajusta estos valores midiendo en Monitor Serial)
// Con potenciómetro en Wokwi: 0 = seco (0%), 4095 = lleno (100%).
// En sensor real de pistas (3.3V): seco = 0% (ADC_SECO = 0), ~80% sumergido dio ~17% (ADC ~700 -> ADC_LLENO = 850).
// Si usas potenciómetro en Wokwi, cambia ADC_LLENO a 4095.
const int ADC_SECO  = 0;
const int ADC_LLENO = 850;

// Módulo Relé 1 Canal para Mini Bomba 5V (alimentado por Arduino Uno 5V)
const int RELAY_PUMP_PIN = 26; // GPIO 26

// Si tu módulo relé activa con HIGH, déjalo así.
// Si activa con LOW (muchos módulos azules optoacoplados), cambia RELAY_ON a LOW y RELAY_OFF a HIGH.
const int RELAY_ON  = HIGH;
const int RELAY_OFF = LOW;

// Micro Servomotor SG90 para ventilación cenital (alimentado a 5V por Arduino Uno)
const int SERVO_VENT_PIN = 18; // GPIO 18 (PWM)

// Motor Paso a Paso 28BYJ-48 + Driver ULN2003 (alimentado a 5V por Arduino Uno)
// PROHIBIDO usar GPIO 12 (pin de arranque/flash del ESP32).
// Pines físicos ULN2003: IN1=19, IN2=23, IN3=5, IN4=13
// Nota: la librería Stepper requiere el orden (IN1, IN3, IN2, IN4) para el 28BYJ-48.
const int STEPPER_IN1 = 19;
const int STEPPER_IN2 = 23;
const int STEPPER_IN3 = 5;
const int STEPPER_IN4 = 13;
const int PASOS_POR_VUELTA = 2048;

// Sensor ambiental interior I2C en GPIO 21 (SDA) / GPIO 22 (SCL):
// Habilitado por defecto con auto-detección de BME280 (Chip ID 0x60) o BMP280 (Chip ID 0x58)
// en direcciones 0x76 y 0x77. Si no hay sensor conectado, hace fallback limpio a DHT11 y 1013.25 hPa.
// Requiere instalar en Arduino IDE: "Adafruit BME280 Library" y "Adafruit BMP280 Library"
// (junto con su dependencia "Adafruit Unified Sensor").
#define USAR_SENSOR_I2C_INTERIOR
#ifdef USAR_SENSOR_I2C_INTERIOR
  #include <Wire.h>
  #include <Adafruit_Sensor.h>
  #include <Adafruit_BME280.h>
  #include <Adafruit_BMP280.h>

  enum TipoSensorI2C {
    I2C_NINGUNO = 0,
    I2C_BME280  = 1,
    I2C_BMP280  = 2
  };

  Adafruit_BME280 bme;
  Adafruit_BMP280 bmp;
  TipoSensorI2C sensorInteriorTipo = I2C_NINGUNO;
  uint8_t sensorInteriorAddr       = 0x00;
#endif
const float PRESION_DEFAULT_HPA = 1013.25;

// Umbral de seguridad anti-cavitación: bajo 20% se apaga y bloquea la bomba
const float UMBRAL_NIVEL_CRITICO = 20.0;

// ============================================================================
// 3. TÓPICOS MQTT OFICIALES (SINCRONIZADOS CON ASAIapp Y MQTTX)
// ============================================================================
// -- Aqui se declaran los topicos donde el ESP32 va a PUBLICAR los datos hacia Android y Web --
// Publicación de telemetría Interior (texto plano)
const char* TOPIC_TEMP      = "ASAI/Temperatura";
const char* TOPIC_HUM       = "ASAI/Humedad";
const char* TOPIC_NIVEL     = "ASAI/Nivel";
const char* TOPIC_DPV       = "ASAI/DPV";
const char* TOPIC_PRESION   = "ASAI/Presion";
const char* TOPIC_BOMBA     = "ASAI/Bomba";
const char* TOPIC_SERVO     = "ASAI/Servo";
const char* TOPIC_ALERTA    = "ASAI/Alerta";

// Publicación de telemetría Exterior (DHT11 en GPIO 4)
const char* TOPIC_EXT_TEMP  = "ASAI/Exterior/Temperatura";
const char* TOPIC_EXT_HUM   = "ASAI/Exterior/Humedad";

// Compatibilidad con ejemplo base de la asignatura
const char* TOPIC_CLASS_TEMP = "ESP8266/Temperatura";
const char* TOPIC_CLASS_HUM  = "ESP8266/Humedad";

// -- Aqui se declaran los topicos a los que el ESP32 se SUSCRIBE para recibir ordenes desde Android --
// Suscripción de comandos desde ASAIapp / MQTTX
const char* TOPIC_CMD_BOMBA      = "ASAI/Bomba/cmd";
const char* TOPIC_CMD_SERVO      = "ASAI/Servo/cmd";
const char* TOPIC_CMD_NUTRIENTES = "ASAI/Nutrientes/cmd";

// ============================================================================
// 4. OBJETOS Y VARIABLES DE ESTADO GLOBAL
// ============================================================================
// -- Aqui se crea el cliente Wi-Fi y el cliente MQTT (PubSubClient) del ESP32 --
WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);
Servo servoVent;
Stepper motorNutrientes(PASOS_POR_VUELTA, STEPPER_IN1, STEPPER_IN3, STEPPER_IN2, STEPPER_IN4);

unsigned long ultimoEnvioMs = 0;
const unsigned long INTERVALO_PUBLICACION_MS = 5000; // Publicar cada 5 segundos sin bloquear

bool bombaEncendida      = false;
int  anguloServoActual   = 0;
float ultimoNivelPct     = 100.0;
float ultimaExtTempC     = 22.0;
float ultimaExtHumPct    = 60.0;
float ultimaIntTempC     = 22.0;
float ultimaIntHumPct    = 60.0;
float ultimaPresionHpa   = PRESION_DEFAULT_HPA;

// ============================================================================
// 5. FUNCIONES AUXILIARES DE HARDWARE Y SEGURIDAD
// ============================================================================

/*
 * Lee el nivel de agua aplicando la técnica anti-electrólisis:
 * Solo energiza GPIO 25 durante 50 ms para tomar la muestra en GPIO 34
 * y vuelve inmediatamente GPIO 25 a LOW para evitar corrosión de las pistas.
 */
float leerNivelEstanque() {
  digitalWrite(LEVEL_VCC_PIN, HIGH);
  delay(50);
  int adcBruto = analogRead(LEVEL_ADC_PIN);
  digitalWrite(LEVEL_VCC_PIN, LOW);

  float porcentaje = 0.0;
  if (ADC_LLENO != ADC_SECO) {
    porcentaje = ((float)(adcBruto - ADC_SECO) * 100.0) / (float)(ADC_LLENO - ADC_SECO);
  }
  if (porcentaje < 0.0)   porcentaje = 0.0;
  if (porcentaje > 100.0) porcentaje = 100.0;

  Serial.print("[NIVEL] ADC crudo=");
  Serial.print(adcBruto);
  Serial.print(" -> ");
  Serial.print(porcentaje, 1);
  Serial.println("%");

  return porcentaje;
}

/*
 * Calcula el Déficit de Presión de Vapor (DPV) en kPa con la fórmula de Tetens.
 */
float calcularDPV(float tempC, float humPct) {
  float svp = 0.61078 * exp((17.27 * tempC) / (tempC + 237.3));
  float avp = svp * (humPct / 100.0);
  float dpv = svp - avp;
  return (dpv < 0.0) ? 0.0 : dpv;
}

/*
 * Control seguro de la bomba con protección local anti-cavitación.
 * Si el estanque está bajo 20%, corta el relé en hardware y publica alerta.
 */
// -- Aqui el ESP32 protege la bomba (< 20%) y PUBLICA su estado y alerta hacia Android --
void aplicarBombaSegura(bool solicitarEncendido, float nivelActual) {
  if (nivelActual < UMBRAL_NIVEL_CRITICO) {
    digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
    if (bombaEncendida || solicitarEncendido) {
      Serial.println("[FAIL-SAFE] Nivel < 20% (" + String(nivelActual, 2) + "%). Bomba APAGADA y bloqueada.");
    }
    bombaEncendida = false;
    if (client.connected()) {
      client.publish(TOPIC_BOMBA, "OFF");
      client.publish(TOPIC_ALERTA, "ESTANQUE_BAJO");
    }
    return;
  }

  bombaEncendida = solicitarEncendido;
  digitalWrite(RELAY_PUMP_PIN, bombaEncendida ? RELAY_ON : RELAY_OFF);

  if (client.connected()) {
    client.publish(TOPIC_BOMBA, bombaEncendida ? "ON" : "OFF");
    client.publish(TOPIC_ALERTA, "NORMAL");
  }
}

/*
 * Desenergiza las 4 bobinas del ULN2003 después de dosificar para que
 * el motor paso a paso no se caliente en reposo.
 */
void apagarBobinasStepper() {
  digitalWrite(STEPPER_IN1, LOW);
  digitalWrite(STEPPER_IN2, LOW);
  digitalWrite(STEPPER_IN3, LOW);
  digitalWrite(STEPPER_IN4, LOW);
}

#ifdef USAR_SENSOR_I2C_INTERIOR
/*
 * Lee el registro 0xD0 (Chip ID) en la dirección I2C indicada.
 * Retorna 0x60 para BME280, 0x58 para BMP280, o 0x00 si no responde.
 */
uint8_t leerChipIdI2C(uint8_t addr) {
  Wire.beginTransmission(addr);
  Wire.write(0xD0);
  if (Wire.endTransmission(true) != 0) {
    return 0x00;
  }
  if (Wire.requestFrom((int)addr, 1) != 1) {
    return 0x00;
  }
  return Wire.read();
}

/*
 * Auto-detecta BME280 (0x60) o BMP280 (0x58) en direcciones 0x76 y 0x77
 * sobre bus I2C GPIO 21 (SDA) / GPIO 22 (SCL) sin bloquear si no hay sensor.
 */
void inicializarSensorI2CInterior() {
  Wire.begin(21, 22);
  sensorInteriorTipo = I2C_NINGUNO;
  sensorInteriorAddr = 0x00;

  const uint8_t direcciones[2] = {0x76, 0x77};
  for (int i = 0; i < 2; i++) {
    uint8_t addr = direcciones[i];
    uint8_t chipId = leerChipIdI2C(addr);

    if (chipId == 0x60) {
      if (bme.begin(addr, &Wire)) {
        sensorInteriorTipo = I2C_BME280;
        sensorInteriorAddr = addr;
        Serial.print("[I2C] BME280 detectado en 0x");
        Serial.print(addr, HEX);
        Serial.println(" (Chip ID 0x60). Temp + Humedad + Presion interiores reales.");
        return;
      }
    } else if (chipId == 0x58 || chipId == 0x56 || chipId == 0x57) {
      if (bmp.begin(addr)) {
        sensorInteriorTipo = I2C_BMP280;
        sensorInteriorAddr = addr;
        Serial.print("[I2C] BMP280 detectado en 0x");
        Serial.print(addr, HEX);
        Serial.println(" (Chip ID 0x58). Temp + Presion reales; humedad interior usa respaldo DHT11.");
        return;
      }
    } else if (chipId != 0x00) {
      // Intento de respaldo si respondió otro ID en 0x76/0x77
      if (bme.begin(addr, &Wire)) {
        sensorInteriorTipo = I2C_BME280;
        sensorInteriorAddr = addr;
        Serial.print("[I2C] BME280 detectado (respaldo) en 0x");
        Serial.println(addr, HEX);
        return;
      }
      if (bmp.begin(addr)) {
        sensorInteriorTipo = I2C_BMP280;
        sensorInteriorAddr = addr;
        Serial.print("[I2C] BMP280 detectado (respaldo) en 0x");
        Serial.print(addr, HEX);
        Serial.println(". Humedad interior usa respaldo DHT11.");
        return;
      }
    }
  }

  Serial.println("[I2C] No se detecto BME280/BMP280 en 0x76 ni 0x77. Fallback a DHT11 y 1013.25 hPa.");
}
#endif

// ============================================================================
// 6. CONEXIÓN WI-FI Y MQTT (ESTRUCTURA DOCENTE OFICIAL)
// ============================================================================

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("[WiFi] Conectando a: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("[WiFi] Conectado correctamente.");
  Serial.print("[WiFi] Dirección IP asignada: ");
  Serial.println(WiFi.localIP());
}

// -- Aqui el ESP32 RECIBE y procesa las ordenes que llegan desde Android o MQTTX --
void callback(char* topic, byte* payload, unsigned int length) {
  String topico = String(topic);
  String mensaje = "";
  for (unsigned int i = 0; i < length; i++) {
    mensaje += (char)payload[i];
  }
  mensaje.trim();

  Serial.print("[MQTT RX] Tópico: ");
  Serial.print(topico);
  Serial.print(" | Mensaje: ");
  Serial.println(mensaje);

  // 1) Comando de Bomba: "ON" / "OFF"
  if (topico == TOPIC_CMD_BOMBA) {
    String cmdUpper = mensaje;
    cmdUpper.toUpperCase();

    // Lectura fresca del nivel antes de decidir encendido (fail-safe inmediato)
    ultimoNivelPct = leerNivelEstanque();

    if (cmdUpper == "ON") {
      if (ultimoNivelPct >= UMBRAL_NIVEL_CRITICO) {
        aplicarBombaSegura(true, ultimoNivelPct);
        Serial.println("[ACTUADOR] Bomba ENCENDIDA por comando MQTT.");
      } else {
        aplicarBombaSegura(false, ultimoNivelPct);
        Serial.println("[SEGURIDAD] Comando ON rechazado: estanque bajo 20%.");
      }
    } else if (cmdUpper == "OFF") {
      aplicarBombaSegura(false, ultimoNivelPct);
      Serial.println("[ACTUADOR] Bomba APAGADA por comando MQTT.");
    }
  }
  // 2) Comando de Servomotor SG90: "0", "45", "90", etc.
  else if (topico == TOPIC_CMD_SERVO) {
    int angulo = mensaje.toInt();
    if (angulo < 0)   angulo = 0;
    if (angulo > 180) angulo = 180;

    anguloServoActual = angulo;
    servoVent.write(anguloServoActual);
    client.publish(TOPIC_SERVO, String(anguloServoActual).c_str());

    Serial.print("[ACTUADOR] Servo SG90 movido a ");
    Serial.print(anguloServoActual);
    Serial.println(" grados.");
  }
  // 3) Comando de Dosificador de Nutrientes (PaP 28BYJ-48): ej. "100"
  else if (topico == TOPIC_CMD_NUTRIENTES) {
    int pasos = mensaje.toInt();
    if (pasos > 0) {
      if (pasos > 4096) pasos = 4096; // Límite de seguridad por comando
      Serial.print("[ACTUADOR] Dosificando nutrientes (");
      Serial.print(pasos);
      Serial.println(" pasos)...");
      motorNutrientes.step(pasos);
      apagarBobinasStepper();
      Serial.println("[ACTUADOR] Dosificación de nutrientes completada.");
    } else {
      Serial.println("[ACTUADOR] Cantidad de pasos inválida para nutrientes.");
    }
  }
}

// -- Aqui el ESP32 se conecta al broker MQTT y se SUSCRIBE a los topicos de comandos --
void reconnect() {
  while (!client.connected()) {
    // Seguridad primero: nunca dejar la bomba corriendo si cae el nivel durante reconexión
    ultimoNivelPct = leerNivelEstanque();
    if (ultimoNivelPct < UMBRAL_NIVEL_CRITICO && bombaEncendida) {
      aplicarBombaSegura(false, ultimoNivelPct);
    }

    Serial.print("[MQTT] Conectando a ");
    Serial.print(mqtt_server);
    Serial.print(" como ");
    Serial.print(mqtt_client_id);
    Serial.print(" ... ");

    if (client.connect(mqtt_client_id)) {
      Serial.println("CONECTADO.");

      // -- Aqui se crean las suscripciones del ESP32 para escuchar comandos desde Android --
      // Suscribirse a los 3 tópicos de comando de ASAIapp / MQTTX
      client.subscribe(TOPIC_CMD_BOMBA);
      client.subscribe(TOPIC_CMD_SERVO);
      client.subscribe(TOPIC_CMD_NUTRIENTES);

      Serial.println("[MQTT] Suscrito a comandos: Bomba, Servo y Nutrientes.");
    } else {
      Serial.print("Falló, rc=");
      Serial.print(client.state());
      Serial.println(". Reintentando en 5 segundos...");
      delay(5000);
    }
  }
}

// ============================================================================
// 7. SETUP Y LOOP PRINCIPAL
// ============================================================================

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== INICIANDO AGROSENSE AI (ASAI) - ESP32 DEVKIT V1 ===");

  // Configurar relé en estado APAGADO desde el primer milisegundo
  digitalWrite(RELAY_PUMP_PIN, RELAY_OFF);
  pinMode(RELAY_PUMP_PIN, OUTPUT);

  // Configurar sensor de nivel con alimentación conmutada en reposo (LOW)
  pinMode(LEVEL_VCC_PIN, OUTPUT);
  digitalWrite(LEVEL_VCC_PIN, LOW);
  pinMode(LEVEL_ADC_PIN, INPUT);

  // Configurar pines del motor paso a paso en LOW en reposo
  pinMode(STEPPER_IN1, OUTPUT);
  pinMode(STEPPER_IN2, OUTPUT);
  pinMode(STEPPER_IN3, OUTPUT);
  pinMode(STEPPER_IN4, OUTPUT);
  apagarBobinasStepper();
  motorNutrientes.setSpeed(10); // 10 RPM suaves para 28BYJ-48

  // Iniciar servo SG90 en 0 grados (compuerta cerrada)
  servoVent.setPeriodHertz(50);
  servoVent.attach(SERVO_VENT_PIN, 500, 2400);
  servoVent.write(anguloServoActual);

  // Iniciar sensor DHT11 (Exterior)
  dht.begin();

  // Auto-detectar sensor I2C Interior (BME280 o BMP280 en GPIO 21/22, sin bloquear)
#ifdef USAR_SENSOR_I2C_INTERIOR
  inicializarSensorI2CInterior();
#else
  Serial.println("[I2C] Sensor I2C interior deshabilitado. Fallback a DHT11 y 1013.25 hPa.");
#endif

  // -- Aqui se enlaza el servidor MQTT y se registra la funcion callback() que escuchara los mensajes --
  // Conectar Wi-Fi y configurar cliente MQTT
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  // Forzar primera publicación inmediata al entrar al loop
  ultimoEnvioMs = millis() - INTERVALO_PUBLICACION_MS;
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  // -- Aqui client.loop() mantiene abierta la escucha de mensajes entrantes desde Android --
  client.loop();

  // -- Aqui el temporizador no bloqueante (millis) dispara la lectura y publicacion cada 5 segundos --
  unsigned long ahoraMs = millis();
  if (ahoraMs - ultimoEnvioMs >= INTERVALO_PUBLICACION_MS) {
    ultimoEnvioMs = ahoraMs;

    // 1. Leer sensor Exterior (DHT11 en GPIO 4) con respaldo a última lectura válida
    float tExtRaw = dht.readTemperature();
    float hExtRaw = dht.readHumidity();
    if (isnan(tExtRaw) || isnan(hExtRaw)) {
      Serial.println("[ADVERTENCIA] Error leyendo DHT11 (Exterior) en GPIO 4. Usando ultima lectura valida.");
    } else {
      ultimaExtTempC  = tExtRaw;
      ultimaExtHumPct = hExtRaw;
    }
    float extTemp = ultimaExtTempC;
    float extHum  = ultimaExtHumPct;

    // 2. Leer sensor Interior (BME280 / BMP280 en GPIO 21/22 o fallback limpio a DHT11)
    float intTemp = extTemp;
    float intHum  = extHum;
    float presionHpa = PRESION_DEFAULT_HPA;
    bool humedadInteriorRespaldoDHT = true;

#ifdef USAR_SENSOR_I2C_INTERIOR
    if (sensorInteriorTipo == I2C_BME280) {
      float tInt = bme.readTemperature();
      float hInt = bme.readHumidity();
      float pInt = bme.readPressure() / 100.0F;

      if (!isnan(tInt) && tInt > -40.0 && tInt < 85.0) {
        ultimaIntTempC = tInt;
        intTemp = tInt;
      } else {
        Serial.println("[ADVERTENCIA] Lectura invalida de temperatura BME280; usando respaldo DHT11.");
      }

      if (!isnan(hInt) && hInt >= 0.0 && hInt <= 100.0) {
        ultimaIntHumPct = hInt;
        intHum = hInt;
        humedadInteriorRespaldoDHT = false;
      } else {
        Serial.println("[ADVERTENCIA] Lectura invalida de humedad BME280; usando respaldo DHT11.");
      }

      if (!isnan(pInt) && pInt > 300.0 && pInt < 1200.0) {
        ultimaPresionHpa = pInt;
        presionHpa = pInt;
      } else {
        presionHpa = ultimaPresionHpa;
      }
    } else if (sensorInteriorTipo == I2C_BMP280) {
      float tInt = bmp.readTemperature();
      float pInt = bmp.readPressure() / 100.0F;

      if (!isnan(tInt) && tInt > -40.0 && tInt < 85.0) {
        ultimaIntTempC = tInt;
        intTemp = tInt;
      } else {
        Serial.println("[ADVERTENCIA] Lectura invalida de temperatura BMP280; usando respaldo DHT11.");
      }

      // BMP280 no posee higrómetro: la humedad interior y el DPV usan respaldo DHT11
      intHum = extHum;
      humedadInteriorRespaldoDHT = true;

      if (!isnan(pInt) && pInt > 300.0 && pInt < 1200.0) {
        ultimaPresionHpa = pInt;
        presionHpa = pInt;
      } else {
        presionHpa = ultimaPresionHpa;
      }
    }
#endif

    // 3. Leer nivel de estanque con pulso anti-electrólisis de 50 ms
    ultimoNivelPct = leerNivelEstanque();

    // 4. Evaluar fail-safe anti-cavitación en cada ciclo
    aplicarBombaSegura(bombaEncendida, ultimoNivelPct);

    // 5. Calcular DPV (kPa) usando temperatura y humedad INTERIOR
    float dpv = calcularDPV(intTemp, intHum);

    // 6. Convertir a texto plano y publicar en todos los tópicos oficiales
    String strExtTemp = String(extTemp, 2);
    String strExtHum  = String(extHum, 2);
    String strIntTemp = String(intTemp, 2);
    String strIntHum  = String(intHum, 2);
    String strNivel   = String(ultimoNivelPct, 2);
    String strDpv     = String(dpv, 2);
    String strPresion = String(presionHpa, 2);
    const char* strBomba  = bombaEncendida ? "ON" : "OFF";
    const char* strAlerta = (ultimoNivelPct < UMBRAL_NIVEL_CRITICO) ? "ESTANQUE_BAJO" : "NORMAL";

    // -- Aqui el ESP32 PUBLICA todos los datos de los sensores cada 5 segundos hacia Android y Web --
    // Telemetría Interior (ASAI/Temperatura, ASAI/Humedad, ASAI/Presion, ASAI/DPV)
    client.publish(TOPIC_TEMP, strIntTemp.c_str());
    client.publish(TOPIC_HUM, strIntHum.c_str());
    client.publish(TOPIC_PRESION, strPresion.c_str());
    client.publish(TOPIC_DPV, strDpv.c_str());

    // Telemetría Exterior (DHT11)
    client.publish(TOPIC_EXT_TEMP, strExtTemp.c_str());
    client.publish(TOPIC_EXT_HUM, strExtHum.c_str());

    // Estanque, actuadores y alerta
    client.publish(TOPIC_NIVEL, strNivel.c_str());
    client.publish(TOPIC_BOMBA, strBomba);
    client.publish(TOPIC_ALERTA, strAlerta);

    // Compatibilidad con ejemplo de clase (DHT11 + MQTT.pdf)
    client.publish(TOPIC_CLASS_TEMP, strExtTemp.c_str());
    client.publish(TOPIC_CLASS_HUM, strExtHum.c_str());

    // 7. Evidencia en Monitor Serial (115200 baudios)
    Serial.println("--------------------------------------------------");
    Serial.print("[EXTERIOR - DHT11 GPIO 4] Temp: ");
    Serial.print(strExtTemp); Serial.print(" C | Hum: ");
    Serial.print(strExtHum);  Serial.println(" %");

    Serial.print("[INTERIOR - ");
#ifdef USAR_SENSOR_I2C_INTERIOR
    if (sensorInteriorTipo == I2C_BME280) {
      Serial.print("BME280 0x");
      Serial.print(sensorInteriorAddr, HEX);
    } else if (sensorInteriorTipo == I2C_BMP280) {
      Serial.print("BMP280 0x");
      Serial.print(sensorInteriorAddr, HEX);
      Serial.print(" | Humedad interior usa respaldo DHT11");
    } else {
      Serial.print("Fallback DHT11 (sin I2C)");
    }
#else
    Serial.print("Fallback DHT11");
#endif
    Serial.print("] Temp: ");   Serial.print(strIntTemp);
    Serial.print(" C | Hum: "); Serial.print(strIntHum);
#ifdef USAR_SENSOR_I2C_INTERIOR
    if (humedadInteriorRespaldoDHT && sensorInteriorTipo == I2C_BMP280) {
      Serial.print(" % (DHT11)");
    } else {
      Serial.print(" %");
    }
#else
    Serial.print(" %");
#endif
    Serial.print(" | Presion: "); Serial.print(strPresion);
    Serial.print(" hPa | DPV: "); Serial.print(strDpv);
    Serial.println(" kPa");

    Serial.print("[SISTEMA] Nivel: "); Serial.print(strNivel);   Serial.print(" % | ");
    Serial.print("Bomba: ");           Serial.print(strBomba);   Serial.print(" | ");
    Serial.print("Servo: ");           Serial.print(anguloServoActual); Serial.print(" deg | ");
    Serial.print("Alerta: ");          Serial.println(strAlerta);
  }
}
