# SPEC-008: Aplicación Móvil Nativa Android (IEI-058 & Feria de Innovación)

> **Documento:** `specs/spec-008-android-app.md`  
> **Estado:** APROBADO PARA IMPLEMENTACIÓN  
> **Carpeta Destino:** `Programacion Android/AgroSenseMobile/` *(a estructurar en Android Studio)*  
> **Fuentes Oficiales:** `PLAN_DE_DESARROLLO_Y_ENTREGABLES_ASAI.md`, `ESPECIFICACION_DATOS_Y_SERVICIOS_ASAI.md`, `specs/spec-009-academic-standards-and-tools.md`  
> **Autor:** `android_engineer` & `academic_compliance`

---

## 1. Objetivo y Alcance
Construir la aplicación móvil Android nativa (**Java** en Android Studio con plantilla **Empty Views Activity**, Minimum SDK **API 24** y Gradle **Kotlin DSL**) que permita controlar y monitorear la **Mini Torre Domiciliaria (`HomeTowerService`)** desde el teléfono para la **Feria de Innovación Santo Tomás**, cumpliendo al 100% los entregables prácticos de **Programación Android (IEI-058)**.

### 1.1. Estándar Técnico de Implementación (Regla Docente IEI-058)
* **Lenguaje:** Exclusivamente **Java** (`MainActivity extends AppCompatActivity`) con `findViewById(...)` para enlazar elementos XML.
* **Concurrencia:** Hilos secundarios clásicos con `new Thread(new Runnable() { ... }).start()` y actualizaciones visuales con `runOnUiThread(new Runnable() { ... })` *(sin Kotlin ni Coroutines)*.
* **Red HTTP nativa:** Cliente usando `java.net.URL` + `HttpURLConnection` (`GET`/`POST`, verificación `getResponseCode()`) y retroalimentación mediante `Toast.makeText(...)`.
* **Permisos y tráfico HTTP local:** `<uses-permission android:name="android.permission.INTERNET" />` en `AndroidManifest.xml` y archivo `res/xml/network_security_config.xml` con `cleartextTrafficPermitted="true"`.

---

## 2. Pantallas y Módulos Requeridos

### 2.1. Pantalla Principal: Monitoreo de Mini Torre (`HomeTowerDashboardActivity`)
* Consume `GET /api/v1/services/home-tower/status` (configurable con IP/URL del servidor FastAPI).
* Muestra en tiempo real:
  * Temperatura (°C) y Humedad Relativa (%).
  * Nivel de Solución en Estanque (%) con indicador visual verde/rojo (umbral `< 20%`).
  * Déficit de Presión de Vapor (`dpv_kpa`).
  * Estado de la Bomba 5V y ángulo del Servomotor SG90.

### 2.2. Control Manual de Actuadores (Cumplimiento Pauta `NodeMCU + Android.pdf`)
* Botones claros e inmediatos:
  * **`Encender Bomba`** / **`Apagar Bomba`** / **`Ciclo 1 Minuto`**.
  * Selector rápido de Ventilación Cenital (`0°`, `45°`, `90°`).
  * Botón de Dosificación de Nutrientes (`+100 pasos`).
* **Modo Dual de Envío:**
  * **Vía Backend SOA (Recomendado):** `POST /api/v1/services/home-tower/actuators/command` con payload:
    ```json
    { "target": "bomba_agua", "action": "ON", "parameter_value": 60, "triggered_by": "ANDROID_APP" }
    ```
  * **Modo Red Local Directa (Fallback Docente):** Petición HTTP GET/POST a la IP local del ESP32 (`/encender`, `/apagar`) si la demostración en aula no pasa por FastAPI.

### 2.3. Calendario y Notificaciones Locales (Integración RF2 + Alertas Críticas)
* Consulta `GET /api/v1/services/field/notification` y/o `GET /api/v1/services/home-tower/safety-check`.
* Dispara notificación local Android (`NotificationCompat`) cuando:
  * El nivel de estanque baja del `20%` (`CRITICAL`).
  * Llega el horario configurado de riego (RF2).

### 2.4. Módulo de Geolocalización y Multimedia (Pauta Semana 13 GPS + Instrucciones)
* Integración con **Google Maps SDK** mostrando la ubicación del módulo hidropónico piloto y/o las sedes de Universidad Santo Tomás según lo requerido en `Semana 13 GPS + Instrucciones.pdf`.
* Soporte de reproducción multimedia (`VideoView`) si la evaluación práctica final mantiene ese requisito.

---

## 3. Criterios de Aceptación (Gherkin)
1. **Control Seguro de Bomba:**
   * **Given** que el estanque está al `82%`, **When** el usuario presiona `"Encender Bomba"` en Android, **Then** el backend registra el comando con `triggered_by: "ANDROID_APP"` (HTTP 200) y la interfaz refleja bomba activa.
2. **Protección Anti-Cavitación en App:**
   * **Given** que el estanque está al `12%` (`< 20%`), **When** el usuario presiona `"Encender Bomba"`, **Then** el backend devuelve HTTP `400` y la app muestra alerta visual explicando el bloqueo de seguridad.
3. **Resiliencia:** La URL base del backend debe ser editable desde ajustes o constante clara de configuración para funcionar con el IP local de la red Wi-Fi de demostración.
