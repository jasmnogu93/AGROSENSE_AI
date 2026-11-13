# SPEC-008: Aplicación Móvil Nativa Android `ASAIapp` (IEI-058 & Feria de Innovación)

> **Documento:** `specs/spec-008-android-app.md`  
> **Estado:** APROBADO PARA IMPLEMENTACIÓN  
> **Carpeta Destino:** `ASAIapp/` *(proyecto Android Studio en la raíz del repositorio)*  
> **Fuentes Oficiales:** `Android + mqtt.pdf`, `Semana 2 - Analista.pdf`, `Semana 4.pdf`, `Semana 10.pdf`, `Semana 13 GPS + Instrucciones.pdf`, `specs/spec-009-academic-standards-and-tools.md`  
> **Autor:** `android_engineer` & `academic_compliance`

---

## 1. Objetivo y Alcance
Construir la aplicación móvil Android nativa **`ASAIapp`** enfocada **exclusivamente en el Servicio 2: `HomeTowerService` (Mini Torre Hidropónica Doméstica — Feria de Innovación Santo Tomás, IoT `IEI-059` y Programación Android `IEI-058`)**, siguiendo estrictamente la metodología, librerías y estructura enseñadas en clase por la Prof. Nicole Ortega para monitorear y controlar la torre en vivo vía **MQTT** y **MQTTX**.

> **Separación de alcance académico:** El servicio de invernadero tradicional de Orquídeas (`AgroFieldService` — Integración de Competencias II) se desarrolla en una aplicación Android separada a cargo de otro integrante de ese ramo; por lo tanto, `ASAIapp` **no incluye calendario de orquídeas ni lógica de `AgroFieldService`**, manteniéndose limpia y dedicada 100% a la Mini Torre Doméstica.

### 1.1. Estándar Técnico de Implementación (Regla Docente `Android + mqtt.pdf`)
* **Configuración del Proyecto:** Plantilla **`Empty Views Activity`**, lenguaje **Java**, Minimum SDK **`API 24`**, Gradle **`Kotlin DSL (build.gradle.kts)`**.
* **Librerías Obligatorias (`gradle/libs.versions.toml` + `app/build.gradle.kts`):**
  * `org.eclipse.paho:org.eclipse.paho.client.mqttv3:1.2.5`
  * `org.eclipse.paho:org.eclipse.paho.android.service:1.1.1`
  * `androidx.localbroadcastmanager:localbroadcastmanager:1.0.0`
  * `com.google.android.gms:play-services-maps:18.1.0` *(para la pantalla de mapa de Semana 13)*
* **Compatibilidad (`gradle.properties`):** `android.useAndroidX=true` y `android.enableJetifier=true` activos.
* **Permisos (`AndroidManifest.xml`):** `<uses-permission android:name="android.permission.INTERNET" />`.
* **Patrón de Código en `MainActivity.java`:**
  * Enlace clásico de vistas con `findViewById(...)` (sin ViewBinding, Kotlin ni Coroutines).
  * Conexión asíncrona mediante **`MqttAsyncClient`** hacia **`tcp://broker.emqx.io:1883`** con `clientId = "AndroidClient_ASAI"` y `MqttConnectOptions` (`setCleanSession(true)`).
  * Recepción de mensajes en `MqttCallback.messageArrived(String topic, MqttMessage message)` reenviando un `Intent("mqtt_data")` con **`LocalBroadcastManager.getInstance(MainActivity.this).sendBroadcast(intent)`**.
  * Actualización de la interfaz desde **`BroadcastReceiver mqttReceiver`** registrado en `onCreate` y desregistrado junto a `mqttClient.disconnect()` en `onDestroy()`.
  * Retroalimentación directa al usuario con **`Toast.makeText(...)`**.

---

## 2. Diseño Visual Minimalista y Contrato de Métricas/Comandos MQTT

La interfaz mantiene un diseño **atractivo, limpio y minimalista** usando únicamente componentes enseñados en clases: `ConstraintLayout`, `LinearLayout`, tarjetas **`CardView`** (`cardCornerRadius="12dp"`, `elevation="8dp"`) con ícono (`ImageView`) + texto (`TextView`), y botones estándar (`Button`).

### 2.1. Métricas en Vivo (Sincronizadas con Web, ESP32 y MQTTX)
La pantalla principal (`activity_main.xml`) suscribe `ASAIapp` a los mismos indicadores mostrados en el Dashboard Web, usando valores simples en texto plano (`Plaintext`, `QoS 0`) para compatibilidad directa con **MQTTX**:

| Tarjeta / Métrica | ID Sugerido (`TextView`) | Tópico MQTT Suscrito | Formato / Unidad | Regla Visual |
| :--- | :--- | :--- | :--- | :--- |
| **Temperatura Ambiental** | `txtTemperature` | `ASAI/Temperatura` | `"Temperatura:\n22.40 °C"` | Color `#FF5722` |
| **Humedad Relativa** | `txtHumidity` | `ASAI/Humedad` | `"Humedad:\n60.50 %"` | Color `#03A9F4` |
| **Nivel de Estanque** | `txtWaterLevel` | `ASAI/Nivel` | `"Nivel Estanque:\n82.00 %"` | Semáforo: Verde `#4CAF50` (`>= 20%`) / Rojo `#F30606` (`< 20%`) |
| **DPV y Presión** | `txtVpd` / `txtPressure` | `ASAI/DPV` y `ASAI/Presion` | `"DPV: 1.05 kPa"` / `"1014.20 hPa"` | Indicador de transpiración saludable |
| **Estado de Bomba / Alerta**| `txtPumpStatus` | `ASAI/Bomba` y `ASAI/Alerta` | `"Bomba: ON/OFF"` | Muestra aviso si ocurre `ESTANQUE_BAJO` |

### 2.2. Panel Minimalista de Control Manual (Publicación MQTT)
Botones simples (`Button` con `setOnClickListener` o `android:onClick`) que publican órdenes vía `mqttClient.publish(topico, new MqttMessage(payload.getBytes()))` y muestran confirmación con `Toast`:

| Control | Acción del Usuario | Tópico MQTT Publicado | Payload | Regla de Seguridad |
| :--- | :--- | :--- | :--- | :--- |
| **Encender / Apagar Bomba 5V** | Tocar botón `Encender Bomba` / `Apagar Bomba` | `ASAI/Bomba/cmd` | `"ON"` / `"OFF"` | Si el último valor recibido de `ASAI/Nivel` es `< 20.0`, bloquea el envío `"ON"` en la UI y muestra `Toast` de alerta anti-cavitación *(además del bloqueo en ESP32 y Backend)*. |
| **Ventilación Cenital (SG90)** | Tocar botón `Abrir 90°` / `Cerrar 0°` | `ASAI/Servo/cmd` | `"90"` / `"0"` | Confirmación por `Toast`. |
| **Dosificar Nutrientes (PaP)** | Tocar botón `Dosificar (+100)` | `ASAI/Nutrientes/cmd` | `"100"` | Confirmación por `Toast`. |

### 2.3. Pantalla Secundaria de Geolocalización (`Semana 13 GPS`)
* Botón limpio en la parte inferior (`Ver Ubicación / Mapa`) que abre una segunda `Activity` usando `Intent` clásico (`startActivity(new Intent(MainActivity.this, MapActivity.class))`), manteniendo la vista principal despejada y minimalista.
* Implementa `SupportMapFragment` con `OnMapReadyCallback`, `LatLng` y `MarkerOptions` según la guía de Semana 13.

---

## 3. Criterios de Aceptación (Gherkin)
1. **Suscripción en Vivo vía MQTTX / ESP32:**
   * **Given** que `ASAIapp` está conectado a `tcp://broker.emqx.io:1883`, **When** el ESP32 (o **MQTTX** en pruebas) publica `"24.50"` en `ASAI/Temperatura` y `"78.00"` en `ASAI/Nivel`, **Then** `MqttCallback.messageArrived` despacha el `Intent("mqtt_data")` por `LocalBroadcastManager` y las tarjetas `CardView` actualizan su texto sin reiniciar la app.
2. **Control de Actuadores Verificable en MQTTX:**
   * **Given** que el nivel recibido en `ASAI/Nivel` es `>= 20%` (ej. `"80.00"`), **When** el usuario presiona `"Encender Bomba"`, **Then** `ASAIapp` publica `"ON"` en `ASAI/Bomba/cmd` (visible al instante en **MQTTX** y recibido por el ESP32) y muestra un `Toast`.
3. **Protección Anti-Cavitación en App:**
   * **Given** que el último valor recibido en `ASAI/Nivel` es `"12.00"` (`< 20%`), **When** el usuario presiona `"Encender Bomba"`, **Then** la tarjeta se marca en rojo (`#F30606`), `ASAIapp` no envía `"ON"` y muestra un `Toast` explicando el bloqueo por estanque bajo.
4. **Higiene de Código Docente:**
   * **Given** el código fuente en `ASAIapp/`, **When** se audita contra `Android + mqtt.pdf` y `spec-009`, **Then** utiliza únicamente Java, `Empty Views Activity`, `CardView`, `MqttAsyncClient`, `LocalBroadcastManager`, `BroadcastReceiver`, `findViewById` y `Intent`.
