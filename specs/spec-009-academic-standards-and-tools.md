# SPEC-009: Estándares Académicos, Herramientas y Plantillas de Clase (IEI-058 / IEI-059 / IEI-094)

> **Documento:** `specs/spec-009-academic-standards-and-tools.md`  
> **Estado:** VIGENTE — FUENTE DE VERDAD ACADÉMICA  
> **Ámbito:** Programación Android (`IEI-058`), Internet de las Cosas (`IEI-059`) e Integración de Competencias II (`IEI-094`)  
> **Docente Android & IoT:** Nicole Ortega Vilugrón (`nortega2@santotomas.cl`)  
> **Propósito:** Rescatar en un solo documento compacto las herramientas, convenciones de programación y rúbricas oficiales exigidas por los ramos para mantener el repositorio libre de PDFs pesados.

---

## 1. Programación Android (`IEI-058`) — Estándar Oficial de Clase

### 1.1. Configuración Obligatoria del Proyecto en Android Studio
Al crear el proyecto `ASAIapp` en Android Studio (`New Project`), respetar exactamente esta configuración enseñada en clases:
* **Carpeta del proyecto en el repositorio:** `ASAIapp/`
* **Plantilla:** `Empty Views Activity` *(NO usar Jetpack Compose ni Empty Activity de Compose)*.
* **Lenguaje:** **Java** *(NO usar Kotlin)*.
* **Minimum SDK:** `API 24 ("Nougat"; Android 7.0)` *(o `API 21+` según plantilla)*.
* **Build configuration language:** `Kotlin DSL (build.gradle.kts) [Recommended]`.

### 1.2. Estructura de Interfaz (XML), Widgets Permitidos y Colores
Solo usar componentes y patrones enseñados explícitamente en clases (`Semana 2`, `Semana 4`, `Semana 10`, `Android + mqtt.pdf`):
* **Layouts permitidos:** `ConstraintLayout`, `LinearLayout` y `TableLayout` / `TableRow`.
* **Tarjetas de métricas (`Android + mqtt.pdf`):** `androidx.cardview.widget.CardView` con `app:cardCornerRadius="12dp"`, `android:elevation="8dp"` y `android:layout_margin="16dp"`, conteniendo un `LinearLayout` horizontal con `ImageView` (`40dp` x `40dp`) y `TextView` (`20sp`, `android:fontFamily="sans-serif-medium"`).
* **Widgets básicos permitidos:** `TextView`, `ImageView`, `Button` (con `android:backgroundTint` y `android:onClick` o `setOnClickListener`), `ProgressBar`, `CheckBox`, `EditText`.
* **Actividad base y enlace de vistas:** `public class MainActivity extends AppCompatActivity` usando `findViewById(R.id.xxx)` dentro de `onCreate` *(sin ViewBinding ni DataBinding)*.
* **Navegación entre pantallas:** `Intent i = new Intent(this, OtraActivity.class); startActivity(i);`.
* **Colores estándar (`res/values/colors.xml` — Semana 10 y `Android + mqtt.pdf`):**
  ```xml
  <color name="gris">#605F5F</color>
  <color name="Verde">#4CAF50</color>
  <color name="Amarillo">#FFC107</color>
  <color name="Rojo">#F30606</color>
  <color name="tempNaranja">#FF5722</color>
  <color name="humedadCeleste">#03A9F4</color>
  ```

### 1.3. Estándar Oficial de Conectividad `Android + MQTT` (`Android + mqtt.pdf`)
La comunicación principal en vivo entre la app Android y el ecosistema IoT debe implementarse con **Eclipse Paho MQTT** y **`LocalBroadcastManager`**:

1. **Permiso en `AndroidManifest.xml`:**
   ```xml
   <uses-permission android:name="android.permission.INTERNET" />
   ```
2. **Catálogo de versiones (`gradle/libs.versions.toml`):**
   ```toml
   [versions]
   pahoMqttClient = "1.2.5"
   pahoMqttAndroidService = "1.1.1"
   androidx_localbroadcastmanager = "1.0.0"

   [libraries]
   paho-mqtt-client = { module = "org.eclipse.paho:org.eclipse.paho.client.mqttv3", version.ref = "pahoMqttClient" }
   paho-mqtt-android = { module = "org.eclipse.paho:org.eclipse.paho.android.service", version.ref = "pahoMqttAndroidService" }
   localbroadcastmanager = "androidx.localbroadcastmanager:localbroadcastmanager:${versions.androidx_localbroadcastmanager}"
   ```
3. **Dependencias y compatibilidad Java 8 (`app/build.gradle.kts`):**
   ```kotlin
   compileOptions {
       sourceCompatibility = JavaVersion.VERSION_1_8
       targetCompatibility = JavaVersion.VERSION_1_8
   }

   dependencies {
       implementation(libs.paho.mqtt.client)
       implementation(libs.paho.mqtt.android)
       implementation(libs.localbroadcastmanager)
   }
   ```
4. **Activación obligatoria de AndroidX y Jetifier (`gradle.properties`):**
   ```properties
   android.useAndroidX=true
   android.enableJetifier=true
   ```
   *(Indispensable para que `org.eclipse.paho.android.service` compile y opere con `androidx`).*
5. **Imports estándar en `MainActivity.java`:**
   ```java
   import androidx.localbroadcastmanager.content.LocalBroadcastManager;
   import org.eclipse.paho.client.mqttv3.IMqttActionListener;
   import org.eclipse.paho.client.mqttv3.IMqttToken;
   import org.eclipse.paho.client.mqttv3.MqttCallback;
   import org.eclipse.paho.client.mqttv3.MqttClient;
   import org.eclipse.paho.client.mqttv3.MqttException;
   import org.eclipse.paho.client.mqttv3.MqttMessage;
   import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
   import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
   import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
   ```
6. **Flujo obligatorio en `MainActivity.java`:**
   * En `onCreate`: inicializar vistas con `findViewById`, llamar a `connectToMqtt()` y registrar el receptor local con:
     `LocalBroadcastManager.getInstance(this).registerReceiver(mqttReceiver, new IntentFilter("mqtt_data"));`
   * En `connectToMqtt()`: instanciar `new MqttAsyncClient("tcp://broker.emqx.io:1883", clientId, null)`, configurar `MqttConnectOptions` con `options.setCleanSession(true);`, conectar con `IMqttActionListener` (`onSuccess` -> `subscribeToTopics()`, `onFailure` -> `Log.e(...)`) y asignar `mqttClient.setCallback(new MqttCallback() { ... })`.
   * En `messageArrived(String topic, MqttMessage message)`: crear `Intent intent = new Intent("mqtt_data");`, discriminar por `topic.equals(...)`, adjuntar el valor con `intent.putExtra(...)` y emitir con `LocalBroadcastManager.getInstance(MainActivity.this).sendBroadcast(intent);`.
   * En `BroadcastReceiver mqttReceiver`: leer `intent.getStringExtra(...)` dentro de `onReceive` y actualizar los `TextView` correspondientes (y publicar comandos a actuadores con `mqttClient.publish(...)`).
   * En `onDestroy()`: desregistrar `mqttReceiver` con `LocalBroadcastManager.getInstance(this).unregisterReceiver(mqttReceiver);` y desconectar `mqttClient.disconnect();`.

### 1.4. Patrones Complementarios de Clase (Hilos y HTTP Local)
* **Hilos clásicos (Semana 10):** Si se requieren tareas periódicas fuera de MQTT, usar `new Thread(new Runnable())` + `runOnUiThread(new Runnable())` *(sin Coroutines ni RxJava)*.
* **HTTP local de referencia (`NodeMCU + Android.pdf`):** `java.net.URL` + `HttpURLConnection` con `res/xml/network_security_config.xml` (`cleartextTrafficPermitted="true"`) y retroalimentación vía `Toast.makeText(...)`.

### 1.5. Multimedia y Geolocalización (`Semana 13 GPS + Instrucciones.pdf`)
* **Video local o remoto:** Widget `<VideoView>` en XML + `MediaController` (`mediaController.setAnchorView(...)`), cargando recursos locales desde `res/raw/` con `"android.resource://" + getPackageName() + "/" + R.raw.nombre_video` o URL directa.
* **Google Maps SDK:**
  * Dependencia en `build.gradle.kts` (`Module :app`):
    `implementation("com.google.android.gms:play-services-maps:18.1.0")`
  * `<meta-data android:name="com.google.android.geo.API_KEY" android:value="..." />` en `AndroidManifest.xml`.
  * Fragmento `<fragment android:id="@+id/maps" android:name="com.google.android.gms.maps.SupportMapFragment" ... />`.
  * En la Activity del mapa: implementar `OnMapReadyCallback`, `GoogleMap.OnMapClickListener` y `GoogleMap.OnMapLongClickListener`, usando `getMapAsync(this)`, `LatLng`, `MarkerOptions` y `CameraUpdateFactory.newLatLng(...)`.

---

## 2. Internet de las Cosas (`IEI-059`) — Herramientas y Patrones de Firmware

### 2.1. Herramientas Oficiales de Trabajo
* **Arduino IDE:** Desarrollo de código `.ino` y verificación en Monitor Serial a **`115200` baudios**.
* **Wokwi Simulator (`sketch.ino`, `diagram.json`, `libraries.txt`):** Entorno de simulación para diseñar circuitos y probar firmware **ESP32** mientras no se cuente con la placa física.
* **MQTTX:** Cliente de escritorio para comprobar publicación y suscripción de tópicos (`Plaintext`, `QoS 0`, `Keep Alive: 60`).

### 2.2. Patrón MQTT de Clase (`DHT11 + MQTT.pdf`, `Semana 8.pdf` y `Android + mqtt.pdf`)
* **Librerías estándar:** `<WiFi.h>` (en ESP32), `<PubSubClient.h>`, `<DHT.h>`.
* **Broker público oficial:** **`broker.emqx.io`** en puerto **`1883`** *(verificado en **MQTTX** con `Plaintext`, `QoS 0`, `Keep Alive: 60`, `Clean Start: true`)*.
* **Estructura modular esperada en el `.ino`:**
  1. `setup_wifi()`: inicia `WiFi.begin(ssid, password)` y espera `WL_CONNECTED` con `delay(500)`/`delay(1000)` imprimiendo IP asignada (`WiFi.localIP()`).
  2. `reconnect()`: bucle `while (!client.connected())` con `client.connect(mqtt_client_name)` (usando un `clientId` único para no colisionar en el broker público) y espera de `5000 ms` entre reintentos.
  3. `setup()`: `Serial.begin(115200);`, inicialización de sensores (`dht.begin()`), `setup_wifi()`, `client.setServer(mqtt_server, mqtt_port)` y `client.setCallback(...)` para comandos entrantes.
  4. `loop()`: asegura conexión (`if (!client.connected()) reconnect(); client.loop();`), valida lecturas (`if (isnan(temperatura) || isnan(humedad))`) y publica **valores simples en texto plano por tópico separado** usando `client.publish(topico, String(valor).c_str())` con temporizador no bloqueante (`millis()`).

### 2.3. Patrón HTTP M2M y Micro-Servidor Local (`Semana 8.pdf` y `NodeMCU + Android.pdf`)
* **Cliente HTTP M2M hacia Backend (POST JSON):**
  ```cpp
  #include <HTTPClient.h>
  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");
  int httpResponseCode = http.POST(jsonData);
  http.end();
  ```
* **Micro-Servidor Web Local en Puerto 80 (control directo desde Android):**
  ```cpp
  #include <WebServer.h> // ESP32 (equivalente a ESP8266WebServer en NodeMCU)
  WebServer server(80);
  // En setup():
  server.on("/encender", HTTP_GET, []() { /* activar salida */ server.send(200, "text/plain", "Encendido"); });
  server.on("/apagar", HTTP_GET, []() { /* apagar salida */ server.send(200, "text/plain", "Apagado"); });
  server.begin();
  // En loop():
  server.handleClient();
  ```

---

## 3. Integración de Competencias II (`IEI-094`) — Requisitos y Evaluación Final

### 3.1. Requerimientos del Caso Base (Cultivo de Orquídeas)
* **Parámetros ambientales objetivo:** Humedad relativa cercana al **`80%`** y temperatura entre **`18 °C – 24 °C`** (noche–día).
* **Funcionalidades obligatorias:**
  1. Calendario semanal de riego y recordatorio/notificación cuando corresponda regar (`RF1`, `RF2`).
  2. Integración de sensores de humedad por **Wi-Fi o Bluetooth** (`RF3`, `RF4`, `RF7`).
  3. Registro histórico de condiciones ambientales en **base de datos relacional** con frecuencia seleccionable por el usuario (ej. cada 1 hora) (`RF5`, `RF6`).

### 3.2. Los 6 Entregables Obligatorios del Examen Final (Semana 16)
1. **Prototipo de Software (MVP)** operativo en demostración en vivo.
2. **Script de cada requerimiento** (`backend/app/routers/field_service.py`, `home_tower_service.py`, `vertical_farm_service.py`).
3. **Script del microcontrolador** (`firmware/`).
4. **Script de la base de datos** (`backend/app/database_schema.sql`).
5. **Plan de pruebas de integración** (`CP-01` a `CP-06`).
6. **Presentación PPT del proyecto** (Problema, Solución, Arquitectura, Pruebas y Conclusiones).

### 3.3. Matriz Oficial de Pruebas de Integración (`CP-01` a `CP-06`)

| ID | Prueba | Condición Inicial | Entrada / Evento | Resultado Esperado |
| :---: | :--- | :--- | :--- | :--- |
| **CP-01** | Lectura de Sensores Ambientales | ESP32 alimentado (5V/USB) y conectado a Wi-Fi | Sensor DHT lee temperatura y humedad | Payload JSON formateado sin errores en Monitor Serial (`115200 baud`) |
| **CP-02** | Ingesta de Telemetría en Backend | Servidor FastAPI en ejecución | Petición `POST /api/v1/telemetry` | Respuesta HTTP `200 OK` y persistencia en BD |
| **CP-03** | Detección de Umbral Crítico | Nivel de estanque `< 20%` (ej. `10%`) | Ingesta de telemetría con nivel crítico | Alerta `ESTANQUE_BAJO` y bloqueo de bomba para evitar trabajo en seco |
| **CP-04** | Activación de Actuador | Nivel óptimo (ej. `80%`) y horario activo | Orden / decisión `decision_action: true` | El ESP32 activa el relé físico y enciende la bomba |
| **CP-05** | Actualización UI en Tiempo Real | Usuario viendo el Dashboard Web | Llegada de nueva telemetría | Valores de temperatura, humedad y bomba cambian sin recargar |
| **CP-06** | Registro en Histórico Ambiental | Transmisión periódica activa | Intervalo cumplido | Inserción en tabla de telemetría con marca temporal UTC auditable |
