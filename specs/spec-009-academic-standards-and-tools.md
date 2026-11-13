# SPEC-009: Estándares Académicos, Herramientas y Plantillas de Clase (IEI-058 / IEI-059 / IEI-094)

> **Documento:** `specs/spec-009-academic-standards-and-tools.md`  
> **Estado:** VIGENTE — FUENTE DE VERDAD ACADÉMICA  
> **Ámbito:** Programación Android (`IEI-058`), Internet de las Cosas (`IEI-059`) e Integración de Competencias II (`IEI-094`)  
> **Docente Android & IoT:** Nicole Ortega Vilugrón (`nortega2@santotomas.cl`)  
> **Propósito:** Rescatar en un solo documento compacto las herramientas, convenciones de programación y rúbricas oficiales exigidas por los ramos para mantener el repositorio libre de PDFs pesados.

---

## 1. Programación Android (`IEI-058`) — Estándar Oficial de Clase

### 1.1. Configuración Obligatoria del Proyecto en Android Studio
Al crear el proyecto en Android Studio (`New Project`), respetar exactamente esta configuración enseñada en clases:
* **Plantilla:** `Empty Views Activity` *(NO usar Jetpack Compose ni Empty Activity de Compose)*.
* **Lenguaje:** **Java** *(NO usar Kotlin)*.
* **Minimum SDK:** `API 24 ("Nougat"; Android 7.0)`.
* **Build configuration language:** `Kotlin DSL (build.gradle.kts) [Recommended]`.

### 1.2. Estructura de Interfaz (XML), Colores y Enlace de Vistas
* **Actividad base:** `public class MainActivity extends AppCompatActivity`
* **Enlace de controles:** Uso clásico con `findViewById(R.id.xxx)` dentro de `onCreate` o un método `private void init()` *(sin ViewBinding ni DataBinding)*.
* **Colores estándar de semáforo (`res/values/colors.xml` — Semana 10):**
  ```xml
  <color name="gris">#605F5F</color>
  <color name="Verde">#4CAF50</color>
  <color name="Amarillo">#FFC107</color>
  <color name="Rojo">#F30606</color>
  ```
* **Manejo de eventos de botones:**
  * Mediante listener: `btn.setOnClickListener(new View.OnClickListener() { @Override public void onClick(View v) { ... } });`
  * O mediante atributo `android:onClick="Start"` en XML con firma `public void Start(View view)` en Java.

### 1.3. Concurrencia, Hilos y Actualización en Tiempo Real (Semana 10)
* Para tareas repetitivas, lecturas periódicas o red, **no** bloquear el hilo principal ni introducir Coroutines/RxJava.
* Usar el patrón estándar de clase con `new Thread(new Runnable())` y `runOnUiThread(new Runnable())`:
  ```java
  new Thread(new Runnable() {
      @Override
      public void run() {
          while (iniciar) {
              // Lógica o lectura periódica en segundo plano
              runOnUiThread(new Runnable() {
                  @Override
                  public void run() {
                      // Actualizar TextView o colores desde el hilo principal
                  }
              });
              try {
                  Thread.sleep(1000);
              } catch (InterruptedException e) {
                  e.printStackTrace();
              }
          }
      }
  }).start();
  ```

### 1.4. Conexión HTTP con Microcontrolador / Backend (`NodeMCU + Android.pdf`)
1. **Permiso en `AndroidManifest.xml`:**
   ```xml
   <uses-permission android:name="android.permission.INTERNET" />
   ```
2. **Tráfico HTTP local sin HTTPS (`res/xml/network_security_config.xml`):**
   Referenciar en `<application android:networkSecurityConfig="@xml/network_security_config">`:
   ```xml
   <?xml version="1.0" encoding="utf-8"?>
   <network-security-config>
       <base-config cleartextTrafficPermitted="true" />
       <domain-config cleartextTrafficPermitted="true">
           <domain includeSubdomains="true">192.168.1.20</domain>
           <domain includeSubdomains="true">10.0.2.2</domain>
       </domain-config>
   </network-security-config>
   ```
3. **Cliente HTTP nativo en Java:**
   Usar `java.net.URL` y `java.net.HttpURLConnection` (`setRequestMethod("GET")` o `"POST"`, `connect()`, `getResponseCode()`) dentro de `new Thread(new Runnable())`, mostrando retroalimentación con `Toast.makeText(MainActivity.this, "...", Toast.LENGTH_SHORT).show()` dentro de `runOnUiThread`.

### 1.5. Multimedia y Geolocalización (`Semana 13 GPS + Instrucciones.pdf`)
* **Video local o remoto:** Widget `<VideoView>` en `activity_main.xml` + `MediaController` (`mediaController.setAnchorView(...)`), cargando recursos locales desde `res/raw/` con `"android.resource://" + getPackageName() + "/" + R.raw.nombre_video` o URL directa.
* **Google Maps SDK:**
  * Dependencia en `build.gradle.kts` (`Module :app`):
    `implementation("com.google.android.gms:play-services-maps:18.1.0")`
  * `<meta-data android:name="com.google.android.geo.API_KEY" android:value="..." />` en `AndroidManifest.xml`.
  * Fragmento `<fragment android:id="@+id/maps" android:name="com.google.android.gms.maps.SupportMapFragment" ... />`.
  * En `MainActivity`: implementar `OnMapReadyCallback`, `GoogleMap.OnMapClickListener` y `GoogleMap.OnMapLongClickListener`, usando `getMapAsync(this)`, `LatLng`, `MarkerOptions` y `CameraUpdateFactory.newLatLng(...)`.

---

## 2. Internet de las Cosas (`IEI-059`) — Herramientas y Patrones de Firmware

### 2.1. Herramientas Oficiales de Trabajo
* **Arduino IDE:** Desarrollo de código `.ino` y verificación en Monitor Serial a **`115200` baudios**.
* **Wokwi Simulator (`sketch.ino`, `diagram.json`, `libraries.txt`):** Entorno de simulación para diseñar circuitos y probar firmware **ESP32** mientras no se cuente con la placa física.
* **MQTTX:** Cliente de escritorio para comprobar publicación y suscripción de tópicos (`Plaintext`, `QoS 0`, `Keep Alive: 60`).

### 2.2. Patrón MQTT de Clase (`DHT11 + MQTT.pdf` y `Semana 8.pdf`)
* **Librerías estándar:** `<WiFi.h>` (en ESP32), `<PubSubClient.h>`, `<DHT.h>`.
* **Brokers públicos usados en clase:** `broker.emqx.io` o `broker.hivemq.com` en puerto **`1883`**.
* **Estructura modular esperada en el `.ino`:**
  1. `setup_wifi()`: inicia `WiFi.begin(ssid, password)` y espera `WL_CONNECTED` con `delay(500)`/`delay(1000)` imprimiendo IP asignada (`WiFi.localIP()`).
  2. `reconnect()`: bucle `while (!client.connected())` con `client.connect(mqtt_client_name)` y espera de `5000 ms` entre reintentos.
  3. `setup()`: `Serial.begin(115200);`, inicialización de sensores (`dht.begin()`), `setup_wifi()` y `client.setServer(mqtt_server, mqtt_port)`.
  4. `loop()`: asegura conexión (`if (!client.connected()) reconnect(); client.loop();`), valida lecturas (`if (isnan(temperatura) || isnan(humedad))`) y publica con `client.publish(topic, payload.c_str())`.

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
2. **Script de cada requerimiento** (`backend/app/routers/field.py`, `home_tower.py`, `vertical_farm.py`).
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
