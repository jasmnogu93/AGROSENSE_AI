# ProyectoServiciosASAI — Ecosistema AgroSense AI Orientado a Servicios

**Versión:** 1.0 (Arquitectura SOA y Microservicios Modulares)  
**Proyecto:** AgroSense AI (ASAI) — Módulo Celular Hidropónico Autónomo  
**Institución:** Santo Tomás (Sede Pedro de Valdivia, Temuco)  
**Equipo:** Jonathan Seguel, Miguel Torres, Integrante 3  
**Fecha:** Noviembre 2026  

---

## 1. Propósito de esta Carpeta

La carpeta `ProyectoServiciosASAI` consolida la **reestructuración estratégica y técnica del proyecto**. Nace de una decisión clave: **desarrollar un único proyecto tecnológico modular que cubra simultáneamente las evaluaciones de 3 asignaturas y la Feria de Innovación**, simplificando el desarrollo mediante una **Arquitectura Orientada a Servicios (SOA)**.

### Los 4 Objetivos Académicos y Profesionales en 1 Solo Proyecto:
1. **Internet de las Cosas (IEI-059 - Prof. Nicole Ortega V.):** Prototipo físico con NodeMCU/ESP32, sensor DHT11, actuador de bomba y mensajería MQTT con HiveMQ.
2. **Programación Android (IEI-058 - Prof. Nicole Ortega V.):** Aplicación móvil nativa en Android Studio con interfaz de control de actuadores, consumo de servicios de red y monitoreo.
3. **Integración de Competencias II (IEI-094):** Prototipo de mediana complejidad (MVP), base de datos relacional, calendario de riego y plan formal de pruebas de integración.
4. **Feria de Innovación Santo Tomás:** Presentación estelar ante jurados e inversores con la maqueta hidropónica física funcionando en vivo y el módulo desacoplado de **Doble Inteligencia Artificial (TypeSafe Jev + DeepSeek)**.

---

## 2. Índice de Documentación en esta Carpeta

Esta suite documental define las reglas del juego antes de escribir una sola línea de código:

| Documento | Descripción y Alcance |
| :--- | :--- |
| 📘 [ARQUITECTURA_ORIENTADA_A_SERVICIOS_ASAI.md](file:///c:/Users/Jonathan/Desktop/Santo%20Tomas/Proyecto%20Feria/ProyectoServiciosASAI/ARQUITECTURA_ORIENTADA_A_SERVICIOS_ASAI.md) | Especificación técnica de los **4 servicios independientes**: límites de responsabilidad, protocolos de enlace (MQTT / REST) y cómo las IAs se integran como servicios "enchufables" sin acoplar el núcleo. |
| 🗄️ [ESPECIFICACION_DATOS_Y_SERVICIOS_ASAI.md](file:///c:/Users/Jonathan/Desktop/Santo%20Tomas/Proyecto%20Feria/ProyectoServiciosASAI/ESPECIFICACION_DATOS_Y_SERVICIOS_ASAI.md) | Contrato de datos: modelos Pydantic simplificados para la bandeja hidropónica, jerarquía de tópicos MQTT en HiveMQ, contrato de la API REST y script SQL de persistencia. |
| 📋 [PLAN_DE_DESARROLLO_Y_ENTREGABLES_ASAI.md](file:///c:/Users/Jonathan/Desktop/Santo%20Tomas/Proyecto%20Feria/ProyectoServiciosASAI/PLAN_DE_DESARROLLO_Y_ENTREGABLES_ASAI.md) | Matriz de cumplimiento cruzado para los 3 ramos, asignación de tareas específicas para los 3 compañeros del equipo y cronograma paso a paso. |
| 🧭 [GUIA_ESTUDIO_Y_MAPA_DEL_SISTEMA.md](../GUIA_ESTUDIO_Y_MAPA_DEL_SISTEMA.md) | Mapa pedagógico completo (6 preguntas: Qué, Por qué, Para quién, Herramientas, Código y SDD) + botiquín de diagnóstico rápido y glosario para defensa de título. |

---

## 3. Resumen Ejecutivo de la Arquitectura de 4 Servicios

```mermaid
flowchart LR
    S1["1. Servicio Hardware IoT<br>(ESP32 + DHT11 + Bomba)"] 
    <-->|MQTT / HiveMQ| 
    S2["2. Servicio Core Backend<br>(FastAPI + Base de Datos)"]

    S2 <-->|API REST / JSON| S3A["3A. Dashboard Web<br>(Jinja2 / Tailwind)"]
    S2 <-->|API REST / MQTT| S3B["3B. App Móvil Android<br>(Android Studio)"]

    S2 <-->|Plug-and-Play (Opcional)| S4["4. Servicio Doble IA<br>(TypeSafe Jev + DeepSeek)"]
```

* **Principio de Tolerancia a Fallos:** Si el servicio de IA o internet se desconectan durante la feria o la evaluación, **el núcleo del sistema (Hardware, Base de Datos, Web y Android) sigue funcionando al 100%** mediante reglas locales y temporizadores de seguridad. Cero puntos únicos de fallo.
