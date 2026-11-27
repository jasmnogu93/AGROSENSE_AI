# SPEC-005: Especificación de Frontend Adaptativo (Multi-Service Hub)

> **Documento:** `specs/spec-005-frontend-adaptive-hub.md`  
> **Estado:** APROBADO  
> **Componente:** `backend/app/templates/index.html`  
> **Autor:** `frontend_ui_engineer` & `academic_compliance`

---

## 1. Experiencia de Usuario y Principios de Diseño
Para permitir que cualquier evaluador docente o jurado de la Feria interactúe con el sistema sin confusiones, el frontend unificado implementa una **Barra de Navegación de Servicios (Tab Switcher)** en la cabecera.

### Pestañas Disponibles:
1. **🌿 Invernadero & Orquídeas (Integración II - RF1 a RF7):**
   * Muestra la tarjeta del **Calendario Semanal de Riego** (con botones interactivos para cada día de la semana `Lun` a `Dom`, selector de hora fija `08:00 hrs`, botón "Guardar Calendario" y caja de notificación activa).
   * Muestra métricas de Orquídeas: Humedad objetivo **80%**, Temperatura **18-24 °C**.
   * Muestra la tabla de histórico de la base de datos SQLite (RF5 y RF6).
2. **🏠 Mini Torre Domiciliaria (Proyecto Feria de Innovación):**
   * Muestra la tarjeta de **Recirculación Continua por Ciclo** (frecuencia en horas y duración de bombeo en minutos).
   * Muestra el estado del **Estanque (Nivel % con sensor resistivo)** y el bloqueo de seguridad anti-cavitación.
   * Muestra telemetría en vivo **Interior (`BME/BMP280`) + Exterior (`DHT11`) + Presión (`hPa`) + DPV** y badge de conexión MQTT (`broker.emqx.io`), actualizándose automáticamente cada **5 segundos** vía `fetch('/api/v1/services/home-tower/status')` sin recargar la página ni perder la pestaña activa.
   * Muestra los controles de **Actuadores Físicos**: Conmutación manual de Bomba 5V, ángulo del Servomotor SG90 (0°-90°) y pasos del Motor PaP dosificador 28BYJ-48 conectados al puente MQTT bidireccional.
3. **🏢 Invernadero Industrial (Visión Escalable):**
   * Muestra un panel de múltiples celdas, comparativa de telemetría distribuida y estado del motor IA Jev.

---

## 2. Requerimientos Técnicos
* **Framework:** HTML5 + Tailwind CSS (vía CDN) + Jinja2 (FastAPI Server-Side Rendering) + Vanilla JavaScript para interactividad asíncrona (Fetch API).
* **Paleta de Color:** Zinc neutral editorial (Vercel/Linear style), fondos `#09090b` y `#18181b`, texto `#f4f4f5`, acentos esmeralda `#10b981` y ámbar `#f59e0b`.
* **Zero Neons / Zero "AI Slop":** Interfaz sobria, tipografía limpia (Inter + JetBrains Mono), botones táctiles y feedback visual instantáneo sin recargar la página.
