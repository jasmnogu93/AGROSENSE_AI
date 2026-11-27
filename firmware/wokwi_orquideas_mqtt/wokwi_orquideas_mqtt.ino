// ============================================================================
// AGROSENSE AI — FIRMWARE ESP32 INVERNADERO DE ORQUÍDEAS (WOKWI + MQTT)
// ============================================================================
// Simulación: https://wokwi.com/projects/481413419177388033
// Pines: Sensor DHT22 en GPIO 4 | Relé / LED de aspersión en GPIO 5
// Red: Wi-Fi ("Wokwi-GUEST") -> broker.emqx.io:1883 -> FastAPI y Supabase
// ============================================================================

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include <ArduinoJson.h>

// Definimos los pines del ESP32 para el sensor y el relé de riego
#define DHTPIN 4       // Pin DATA conectado al DHT22
#define DHTTYPE DHT22
#define RELAY_PIN 5    // Pin digital para activar la bomba / LED de riego

// Datos de red Wi-Fi y broker MQTT público usados en el enlace (RF3)
const char* ssid        = "Wokwi-GUEST";
const char* password    = "";
const char* mqtt_server = "broker.emqx.io";
const int   mqtt_port   = 1883;

// Tópicos dedicados del invernadero de Orquídeas en el broker público
const char* TOPIC_ORQ_TEMP      = "ASAI/Orquideas/Temperatura";
const char* TOPIC_ORQ_HUM       = "ASAI/Orquideas/Humedad";
const char* TOPIC_ORQ_BOMBA     = "ASAI/Orquideas/Bomba";
const char* TOPIC_ORQ_BOMBA_CMD = "ASAI/Orquideas/Bomba/cmd";

WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

// Usamos millis() para contar el intervalo sin congelar la escucha de comandos MQTT
unsigned long tiempoAnterior = 0;
const long intervalo = 3000;
bool estadoBomba = false;

// Actuador físico: enciende o apaga el relé del Pin 5 y confirma estado en MQTT
void aplicarBomba(bool encender) {
  estadoBomba = encender;
  digitalWrite(RELAY_PIN, estadoBomba ? HIGH : LOW);
  if (client.connected()) {
    client.publish(TOPIC_ORQ_BOMBA, estadoBomba ? "ON" : "OFF");
  }
  Serial.print(">>> COMANDO EJECUTADO: La bomba ahora está ");
  Serial.println(estadoBomba ? "ENCENDIDA" : "APAGADA");
}

// Esta función callback recibe los comandos "ON" / "OFF" enviados desde la web por MQTT
void callback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  msg.trim();

  if (String(topic) == TOPIC_ORQ_BOMBA_CMD) {
    if (msg.equalsIgnoreCase("ON") || msg == "true") {
      aplicarBomba(true);
    } else if (msg.equalsIgnoreCase("OFF") || msg == "false") {
      aplicarBomba(false);
    } else {
      // Usamos ArduinoJson para leer mensajes en formato JSON como {"bomba": true}
      StaticJsonDocument<128> doc;
      if (!deserializeJson(doc, msg) && doc.containsKey("bomba")) {
        aplicarBomba(doc["bomba"]);
      }
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    String clientId = "ESP32_Wokwi_Orq_" + String(random(1000, 9999));
    if (client.connect(clientId.c_str())) {
      client.subscribe(TOPIC_ORQ_BOMBA_CMD);
      Serial.println("[MQTT] Conectado a broker.emqx.io (Orquideas)");
    } else {
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);

  dht.begin();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  WiFi.begin(ssid, password);
  Serial.print("[WiFi] Conectando a Wokwi-GUEST");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Conectado.");

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);

  Serial.println("Iniciando AgroSense AI (Modo Wokwi Orquideas)...");
  Serial.println("Escribe {\"bomba\": true} o {\"bomba\": false} para probar el relé.");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Lectura local por Monitor Serial
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    StaticJsonDocument<200> docIn;
    DeserializationError error = deserializeJson(docIn, input);
    if (!error && docIn.containsKey("bomba")) {
      aplicarBomba(docIn["bomba"]);
    }
  }

  // En esta parte leemos el DHT22 cada 3 segundos con millis() para cumplir el RF4 sin pausar el ESP32
  unsigned long tiempoActual = millis();
  if (tiempoActual - tiempoAnterior >= intervalo) {
    tiempoAnterior = tiempoActual;

    float humedad = dht.readHumidity();
    float temperatura = dht.readTemperature();

    if (isnan(humedad) || isnan(temperatura)) {
      Serial.println("{\"error\": \"Fallo al leer el sensor DHT22\"}");
      return;
    }

    // Publica lecturas en texto plano al broker MQTT hacia la Web y Supabase
    client.publish(TOPIC_ORQ_TEMP, String(temperatura, 2).c_str());
    client.publish(TOPIC_ORQ_HUM, String(humedad, 2).c_str());
    client.publish(TOPIC_ORQ_BOMBA, estadoBomba ? "ON" : "OFF");

    // Imprime el mismo estado en formato JSON por Monitor Serial (115200 baud)
    StaticJsonDocument<200> docOut;
    docOut["temp"] = temperatura;
    docOut["hum"] = humedad;
    docOut["estado_bomba"] = estadoBomba;
    serializeJson(docOut, Serial);
    Serial.println();
  }
}
