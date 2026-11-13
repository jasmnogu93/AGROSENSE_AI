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
const char* ssid     = "TU_WIFI";       // <-- Nombre de tu Wi-Fi (debe ser 2.4 GHz)
const char* password = "TU_PASSWORD";   // <-- Contraseña de tu Wi-Fi

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
// En sensor real de pistas: prueba fuera del agua (ADC_SECO) y sumergido (ADC_LLENO).
const int ADC_SECO  = 0;
const int ADC_LLENO = 4095;

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

// Presión barométrica por defecto (hPa) si no se conecta BME280 en GPIO 21/22.
// Para usar BME280 real por I2C (SDA=21, SCL=22), instala "Adafruit BME280 Library"
// y descomenta la línea #define USAR_BME280.
// #define USAR_BME280
#ifdef USAR_BME280
  #include <Wire.h>
  #include <Adafruit_BME280.h>
  Adafruit_BME280 bme;
  bool bmeDisponible = false;
#endif
const float PRESION_DEFAULT_HPA = 1013.25;

// Umbral de seguridad anti-cavitación: bajo 20% se apaga y bloquea la bomba
const float UMBRAL_NIVEL_CRITICO = 20.0;

// ============================================================================
// 3. TÓPICOS MQTT OFICIALES (SINCRONIZADOS CON ASAIapp Y MQTTX)
// ============================================================================
// Publicación de telemetría (texto plano)
const char* TOPIC_TEMP      = "ASAI/Temperatura";
const char* TOPIC_HUM       = "ASAI/Humedad";
const char* TOPIC_NIVEL     = "ASAI/Nivel";
const char* TOPIC_DPV       = "ASAI/DPV";
const char* TOPIC_PRESION   = "ASAI/Presion";
const char* TOPIC_BOMBA     = "ASAI/Bomba";
const char* TOPIC_SERVO     = "ASAI/Servo";
const char* TOPIC_ALERTA    = "ASAI/Alerta";

// Compatibilidad con ejemplo base de la asignatura
const char* TOPIC_CLASS_TEMP = "ESP8266/Temperatura";
const char* TOPIC_CLASS_HUM  = "ESP8266/Humedad";

// Suscripción de comandos desde ASAIapp / MQTTX
const char* TOPIC_CMD_BOMBA      = "ASAI/Bomba/cmd";
const char* TOPIC_CMD_SERVO      = "ASAI/Servo/cmd";
const char* TOPIC_CMD_NUTRIENTES = "ASAI/Nutrientes/cmd";

// ============================================================================
// 4. OBJETOS Y VARIABLES DE ESTADO GLOBAL
// ============================================================================
WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);
Servo servoVent;
Stepper motorNutrientes(PASOS_POR_VUELTA, STEPPER_IN1, STEPPER_IN3, STEPPER_IN2, STEPPER_IN4);

unsigned long ultimoEnvioMs = 0;
const unsigned long INTERVALO_PUBLICACION_MS = 5000; // Publicar cada 5 segundos sin bloquear

bool bombaEncendida    = false;
int  anguloServoActual = 0;
float ultimoNivelPct   = 100.0;
float ultimaTempC      = 22.0;
float ultimaHumPct     = 60.0;

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

  // Iniciar sensor DHT
  dht.begin();

  // Iniciar BME280 solo si está habilitado (no bloquea si no está conectado)
#ifdef USAR_BME280
  Wire.begin(21, 22);
  if (bme.begin(0x76) || bme.begin(0x77)) {
    bmeDisponible = true;
    Serial.println("[I2C] BME280 detectado en GPIO 21/22.");
  } else {
    bmeDisponible = false;
    Serial.println("[I2C] BME280 no detectado. Usando 1013.25 hPa por defecto.");
  }
#else
  Serial.println("[I2C] Presión por defecto habilitada (1013.25 hPa).");
#endif

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
  client.loop();

  unsigned long ahoraMs = millis();
  if (ahoraMs - ultimoEnvioMs >= INTERVALO_PUBLICACION_MS) {
    ultimoEnvioMs = ahoraMs;

    // 1. Leer sensores ambientales (DHT)
    float t = dht.readTemperature();
    float h = dht.readHumidity();
    if (isnan(t) || isnan(h)) {
      Serial.println("[ADVERTENCIA] Error leyendo DHT en GPIO 4. Usando última lectura válida.");
      t = ultimaTempC;
      h = ultimaHumPct;
    } else {
      ultimaTempC  = t;
      ultimaHumPct = h;
    }

    // 2. Leer presión barométrica (BME280 si está activo o 1013.25 hPa por defecto)
    float presionHpa = PRESION_DEFAULT_HPA;
#ifdef USAR_BME280
    if (bmeDisponible) {
      float p = bme.readPressure() / 100.0F;
      if (!isnan(p) && p > 300.0 && p < 1200.0) {
        presionHpa = p;
      }
    }
#endif

    // 3. Leer nivel de estanque con pulso anti-electrólisis de 50 ms
    ultimoNivelPct = leerNivelEstanque();

    // 4. Evaluar fail-safe anti-cavitación en cada ciclo
    aplicarBombaSegura(bombaEncendida, ultimoNivelPct);

    // 5. Calcular DPV (kPa)
    float dpv = calcularDPV(ultimaTempC, ultimaHumPct);

    // 6. Convertir a texto plano y publicar en todos los tópicos oficiales
    String strTemp    = String(ultimaTempC, 2);
    String strHum     = String(ultimaHumPct, 2);
    String strNivel   = String(ultimoNivelPct, 2);
    String strDpv     = String(dpv, 2);
    String strPresion = String(presionHpa, 2);
    const char* strBomba  = bombaEncendida ? "ON" : "OFF";
    const char* strAlerta = (ultimoNivelPct < UMBRAL_NIVEL_CRITICO) ? "ESTANQUE_BAJO" : "NORMAL";

    client.publish(TOPIC_TEMP, strTemp.c_str());
    client.publish(TOPIC_HUM, strHum.c_str());
    client.publish(TOPIC_NIVEL, strNivel.c_str());
    client.publish(TOPIC_DPV, strDpv.c_str());
    client.publish(TOPIC_PRESION, strPresion.c_str());
    client.publish(TOPIC_BOMBA, strBomba);
    client.publish(TOPIC_ALERTA, strAlerta);

    // Compatibilidad con ejemplo de clase (DHT11 + MQTT.pdf)
    client.publish(TOPIC_CLASS_TEMP, strTemp.c_str());
    client.publish(TOPIC_CLASS_HUM, strHum.c_str());

    // 7. Evidencia en Monitor Serial (115200 baudios)
    Serial.println("--------------------------------------------------");
    Serial.print("Temp: ");    Serial.print(strTemp);    Serial.print(" C | ");
    Serial.print("Hum: ");     Serial.print(strHum);     Serial.print(" % | ");
    Serial.print("DPV: ");     Serial.print(strDpv);     Serial.println(" kPa");
    Serial.print("Nivel: ");   Serial.print(strNivel);   Serial.print(" % | ");
    Serial.print("Presion: "); Serial.print(strPresion); Serial.println(" hPa");
    Serial.print("Bomba: ");   Serial.print(strBomba);   Serial.print(" | ");
    Serial.print("Servo: ");   Serial.print(anguloServoActual); Serial.print(" deg | ");
    Serial.print("Alerta: ");  Serial.println(strAlerta);
  }
}
