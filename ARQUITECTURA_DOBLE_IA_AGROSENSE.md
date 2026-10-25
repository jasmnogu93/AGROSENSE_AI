# AgroSense AI — Especificación de Arquitectura y Ecosistema de Doble IA

Este documento consolida la visión técnica y funcional del proyecto **AgroSense AI**, detallando la distribución de roles entre el hardware en terreno, el backend en la nube (FastAPI sobre Azure) y el modelo de **Doble Inteligencia Artificial** (**JEV** y **LLM Cognitivo**), incluyendo la interacción de datos y la función conversacional **"Habla con tu Granja"**.

---

## 1. Visión General del Sistema

**AgroSense AI** es una plataforma ciberfísica e integral de agricultura de precisión, riego inteligente y orquestación de flota autónoma (electrobombas, válvulas, drones de pulverización y maquinaria agrícola). 

El sistema está concebido bajo una premisa fundamental: **tolerancia a fallos de conectividad en zonas rurales (*Offline-First*)**, combinando la inmediatez de la respuesta física en terreno con la capacidad de razonamiento avanzado y orquestación multi-maquinaria en la nube.

---

## 2. El Ecosistema de Doble Inteligencia Artificial

Para no sobrecargar los microcontroladores y garantizar tanto velocidad instantánea como profundidad analítica, la inteligencia se desacopla estrictamente en dos niveles complementarios:

```mermaid
flowchart TD
    subgraph Campo ["Capa Física (Terreno)"]
        SENSORES["Sensores de Campo<br>(Humedad, Temperatura, pH, Cámaras Dron)"]
        FLOTA["Flota y Actuadores<br>(Bomba de Riego, Electroválvulas, Drones, Tractores)"]
    end

    subgraph BackendAzure ["Capa Cloud Backend (FastAPI en Microsoft Azure)"]
        GATEWAY["API Gateway / FastAPI<br>(Validación de Esquemas Pydantic)"]
        DB[(Base de Datos Cloud<br>Telemetría, Históricos y Auditoría)]
    end

    subgraph DobleIA ["Capa de Inteligencia Dual"]
        JEV["1. IA Operativa: JEV<br>(Motor de Decisión y Control Numérico en Tiempo Real)"]
        LLM["2. IA Cognitiva: LLM Grande<br>(DeepSeek / Gemini / GPT - Mejor Costo/Rendimiento)"]
    end

    subgraph Usuarios ["Interfaces de Usuario"]
        APP["App Android (Offline-First) / Web Dashboard"]
    end

    %% Conexiones Terreno - Cloud
    SENSORES -->|Telemetría continua (WebSockets/REST)| GATEWAY
    GATEWAY -->|Persistencia| DB
    GATEWAY <-->|Flujo de inferencia frecuente (segundos)| JEV
    JEV -->|Señales de control estructuradas| FLOTA

    %% Interacción Dual IA
    JEV -.->|Alertas de anomalías / Eventos críticos / Plagas| LLM
    LLM -->|Recalibración de parámetros y recetas de cultivo| JEV
    LLM <-->|Consultas SQL/NoSQL a históricos y telemetría| DB

    %% Interacción Usuario
    APP <-->|Monitoreo y Mando| GATEWAY
    APP <-->|'Habla con tu Granja' (Chat botánico y diagnóstico)| LLM
```

---

## 3. IA 1: TypeSafe Jev (jevai.net — Modelo de Decisiones System One)

> [!IMPORTANT]
> **Definición Oficial de JEV en el Proyecto:**  
> Cuando en este proyecto y en la documentación técnica se menciona **JEV**, nos referimos explícitamente a **TypeSafe Jev (`jevai.net`)**, la inteligencia artificial de decisiones desarrollada por TypeSafe AI (fundada por ex-investigadores de OpenAI). No es un generador de texto ni un simple script: es un modelo discriminativo *"System 1"* de alta velocidad optimizado para inferencia máquina a máquina vía API (`typesafe/jev-latest` en OpenRouter).

### 3.1 Propósito y Filosofía
JEV **no genera texto libre** ni es un chatbot. Es un motor de inferencia y orquestación de políticas de control que opera en la nube a través de la API de Decisiones. 

A diferencia de la programación tradicional basada en `if / else` rígidos, JEV procesa el estado completo de la granja (humedad, temperatura, pH, viento, batería) y resuelve compromisos multidimensionales en tiempo real evaluando preguntas tipadas en una sola pasada paralela de alta velocidad (70 a 200 ms).

### 3.2 Las 3 Primitivas Nativas de Decisión de JEV
TypeSafe Jev estructura sus decisiones en torno a 3 tipos de preguntas fundamentales:
1. **Noul ("Sí o No" / Booleano con Probabilidad)**: Determina inequívocamente si una maniobra física (ej: activación de bomba de riego o protocolo de helada) está autorizada o debe bloquearse (`true / false`).
2. **Score ("0 a 100" / Modulación Continua Ponderada)**: Evalúa el estado sobre una escala ordenada (niveles del 0% al 100%) para definir la potencia de la electrobomba, el grado de apertura de una electroválvula o la velocidad de un actuador.
3. **Choice ("Decisiones de la Lista de Herramientas")**: Selecciona la herramienta específica dentro del catálogo de la flota (`ninguna`, `bomba_riego_principal`, `calefactor_antihelada_sec1`, `electrovalvula_cuartel_01`, `dron_fumigador_alfa`).

### 3.3 Escalabilidad Futura de la Flota
Cuando la granja incorpore nuevos equipos (drones, brazos robóticos o sensores de savia), **no se requiere reprogramar el código de los microcontroladores en terreno**. La nueva maquinaria simplemente se registra en el catálogo de herramientas de FastAPI, y JEV aprende a orquestarla dentro de su lógica global en la nube.

### 3.4 Manejo de Caídas de Red (*Fail-Safe* & *Lease Time*)
Para evitar riesgos si se corta internet:
* Cada orden emitida por JEV tiene un **tiempo de vigencia** (*lease time*, ej. 15 minutos).
* Si el hardware en terreno pierde el "latido" (*heartbeat*) de JEV, la maquinaria finaliza su ciclo seguro y conmuta a un estado de prevención local (*Hold/Failsafe*), evitando desbordes o daños mecánicos.

---

## 4. IA 2: LLM Cognitivo (DeepSeek / Gemini / GPT)

### 4.1 Propósito
Es el "Cerebro Consultor y Agrónomo Investigador". Se utiliza un modelo de lenguaje de última generación optimizado en relación costo-rendimiento. Este modelo no procesa el bucle de control de cada segundo, sino que interviene en tres escenarios de alto valor analítico:

### 4.2 Funciones Principales

#### A. Diagnóstico Fitosanitario y Detección de Anomalías Complejas
Cuando JEV o los drones detectan un patrón anómalo (como una caída brusca de pH, manchas foliares por visión artificial o estrés hídrico focalizado):
* El LLM recibe el contexto completo: telemetría de 72 horas, imágenes multiespectrales y condiciones ambientales.
* Identifica la plaga, hongo o deficiencia nutricional y genera un plan de remediación agronómica.

#### B. Investigación Agronómica Profunda en Tiempo Real
El LLM cuenta con acceso a herramientas de consulta para buscar información especializada según el tipo de planta, variedad y suelo (por ejemplo, arándanos, avellanos europeos o cerezos en suelos volcánicos de La Araucanía):
* **Recalibración de JEV**: El LLM traduce la investigación en directivas numéricas para JEV (*"Para este cultivo en su fase fenológica actual, reajusta el umbral mínimo de humedad al 35% y programa la aplicación de micronutrientes foliares al atardecer"*).

#### C. Informes Periódicos Consolidados
Genera de manera automática resúmenes semanales y mensuales en lenguaje humano claro, detallando ahorro de agua (en litros y porcentaje), horas de bombeo, eficiencia energética y proyecciones de salud del cultivo.

---

## 5. Nueva Funcionalidad: "Habla con tu Granja"

### 5.1 Concepto
Es la interfaz conversacional entre el agricultor y su explotación agrícola, integrada en la aplicación móvil de Android y el Dashboard Web de Azure.

```mermaid
sequenceDiagram
    autonumber
    actor U as Agricultor (Celular / Web)
    participant L as LLM Cognitivo ("Habla con tu Granja")
    participant API as FastAPI Backend (Azure)
    participant DB as Base de Datos (Telemetría / Históricos)
    participant J as Motor JEV (Estado Operativo)

    U->>L: "¿Por qué se activó el riego hoy a las 06:00 AM y cómo está el pH?"
    Note over L: El LLM determina que necesita<br>datos reales de la granja (Tool Calling)
    L->>API: query_farm_data(time="06:00", metrics=["irrigation", "pH"])
    API->>DB: Consultar telemetría e histórico de eventos
    API->>J: Consultar justificación de la decisión tomada
    DB-->>API: Registros obtenidos
    J-->>API: JEV activó bomba al 70% por humedad &lt; 18% previa al amanecer
    API-->>L: Datos consolidados (pH: 6.4, Riego: 70%, Humedad: 17.8%)
    L-->>U: "El riego se inició a las 06:00 porque la humedad del suelo había caído al 17.8%, y JEV aprovechó antes del amanecer para evitar evaporación solar. Tu pH se mantiene en 6.4, un nivel ideal para tus plantas."
```

### 5.2 Capacidades de la Función:
* **Consultas de Estado en Tiempo Real**: *"¿Cómo están los sectores del fondo?", "¿Cuánta agua hemos consumido esta semana?"*.
* **Explicabilidad de Decisiones**: Responde por qué JEV tomó o canceló una acción (eliminando la sensación de "caja negra").
* **Recomendaciones y Consejos Agronómicos**: Brinda tips personalizados de manejo de suelo, poda o fertilización según las variables reales registradas en los sensores.

---

## 6. Matriz de Comunicación: ¿Quién se comunica con quién?

| Emisor | Receptor | Protocolo / Canal | Tipo de Información Transmitida |
| :--- | :--- | :--- | :--- |
| **Sensores / ESP32** | **FastAPI Backend** | WebSockets (`/ws/telemetry`) / REST HTTPS | Lecturas de humedad, temperatura, pH, nivel de estanque y *heartbeat*. |
| **FastAPI Backend** | **Motor JEV (API)** | REST asíncrono interno / gRPC | Envío de telemetría normalizada y recepción de señales (`true/false`, `0-100%`, `tool_id`). |
| **FastAPI Backend** | **Flota / Actuadores** | MQTT / WebSockets / CoAP | Despacho de comandos de encendido/apagado, potencia y trayectorias. |
| **FastAPI / JEV** | **Base de Datos Azure** | Conexión segura SQL / NoSQL | Histórico de sensores, auditoría de activaciones de JEV y consumos. |
| **FastAPI Backend** | **LLM Cognitivo** | HTTPS API (OpenAI / DeepSeek / Gemini SDK) | Peticiones de diagnóstico de emergencias, reportes semanales y prompts de "Habla con tu Granja". |
| **LLM Cognitivo** | **FastAPI / DB** | Function Calling / Tool Calling (vía API) | Consultas automáticas a tablas de telemetría y ejecución de recetas botánicas. |
| **LLM Cognitivo** | **Motor JEV** | Interfaz interna FastAPI | Inyección de nuevos límites y perfiles de calibración para la toma de decisiones. |
| **App Android / Web** | **FastAPI Backend** | REST HTTPS + WebSockets | Visualización del tablero en tiempo real, cambio de modos (Auto/Manual) y chat con la granja. |

---

## 7. Plan de Concreción Inmediata: La Entrega de "Computación en la Nube"

Para aterrizar esta arquitectura y cumplir con la evaluación sumativa de Santo Tomás (40% de la nota):

1. **Construcción del Microservicio Backend**: Creación del contenedor con FastAPI que sirva tanto la API de telemetría como un **Dashboard Web interactivo** de AgroSense AI.
2. **Dockerización Local**: Creación del `Dockerfile` multietapa optimizado y ejecución local con evidencias.
3. **Publicación en Azure Container Registry (ACR)**: Empaquetado y subida de la imagen.
4. **Despliegue en Azure Container Instances (ACI)**: Puesta en marcha con FQDN (URL pública accesible para el docente y la comisión de la feria).
5. **Informe de Evidencias**: Documento con capturas paso a paso que asegura la nota máxima según la rúbrica institucional.
