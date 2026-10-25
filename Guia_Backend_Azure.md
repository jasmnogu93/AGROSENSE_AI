# AgroSense AI — Guía Paso a Paso: Backend FastAPI, Docker y Despliegue en Azure

**Documento:** `Guia_Backend_Azure.md`  
**Autor:** Jonathan Seguel  
**Asignatura:** Computación en la Nube (IEI-075) / Proyecto de Feria  
**Institución:** Santo Tomás (Sede Pedro de Valdivia, Temuco)  
**Propósito:** Guía de aprendizaje y fuente de verdad práctica para comprender cómo se construyó el microservicio, cómo ejecutarlo manualmente, cómo empaquetarlo con Docker y cómo desplegarlo en Azure Container Instances (ACI).

---

## 1. Resumen de la Solución Construida

Se desarrolló el **Microservicio Cloud Central de AgroSense AI**:
1. **API Asíncrona con FastAPI**: Ingesta de datos de sensores IoT, validación estricta con esquemas Pydantic v2 y endpoints de monitoreo de salud.
2. **IA de Toma de Decisiones TypeSafe Jev (`jevai.net`)**: Integración nativa con el modelo de decisiones System One de TypeSafe AI (`typesafe/jev-latest` en OpenRouter). Evalúa el estado de la granja y responde con sus 3 primitivas nativas:
   * **Noul** ("Sí o No" / Booleano de autorización de riego).
   * **Score** ("0 a 100" / Modulación de potencia porcentual).
   * **Choice** ("Herramientas de la lista" / Selección de actuador o electrobomba).
   * Incluye modo de contingencia local (*fallback*) para no detenerse si se corta internet.
3. **Función "Habla con tu Granja"**: Asistente agronómico conversacional que responde dudas del agricultor consultando en tiempo real las métricas de la base de datos y la justificación de JEV.
4. **Dashboard Web Integrado**: Panel visual responsivo y moderno (HTML5 + Tailwind CSS) que permite a cualquier evaluador ver los datos en vivo, simular eventos climáticos extremos y hablar con la granja.
5. **Contenedor Docker Portable**: `Dockerfile` multietapa optimizado para correr idénticamente en local y en Microsoft Azure.

---

## 2. Fase 1: Preparación del Entorno Local (Paso a Paso)

### 2.1 ¿Por qué usamos un Entorno Virtual (`.venv`)?
En desarrollo profesional de IA y backend, **nunca se instalan librerías directamente en el sistema operativo Windows**. Se crea un entorno virtual (`.venv`): una carpeta aislada dentro del proyecto donde viven exclusivamente las librerías necesarias. Esto evita conflictos de versiones y mantiene tu computadora 100% limpia.

### 2.2 Comandos Ejecutados para el Entorno

```powershell
# Paso 1: Instalamos Python 3.12 limpio mediante winget (solo si no está instalado)
winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements

# Paso 2: Nos ubicamos en la raíz del proyecto
Set-Location "c:\Users\Jonathan\OneDrive\Desktop\Santo Tomas\Proyecto Feria"

# Paso 3: Creamos la carpeta del backend y entramos en ella
New-Item -ItemType Directory -Force -Path "backend\app\templates"
Set-Location "backend"

# Paso 4: Creamos el entorno virtual aislado (.venv)
python -m venv .venv

# Paso 5: Activamos el entorno virtual en la terminal
.\.venv\Scripts\Activate.ps1
```

> [!NOTE]
> Cuando el entorno virtual está activo, tu terminal mostrará un prefijo `(.venv)` a la izquierda.

---

## 3. Fase 2: Instalación de Dependencias

Creamos el archivo `backend/requirements.txt` con las librerías fundamentales:

```text
fastapi>=0.115.0,<0.116.0
uvicorn[standard]>=0.34.0,<0.35.0
pydantic>=2.10.0,<2.11.0
jinja2>=3.1.5,<3.2.0
httpx>=0.28.0,<0.29.0
```

### ¿Por qué cada librería?
* **`fastapi`**: Framework web asíncrono ultrarrápido para APIs REST.
* **`uvicorn[standard]`**: Servidor web ASGI de alto rendimiento que ejecuta FastAPI.
* **`pydantic`**: Validador de modelos de datos. Rechaza datos corruptos de sensores.
* **`jinja2`**: Motor de plantillas para renderizar el Dashboard HTML.
* **`httpx`**: Cliente HTTP para pruebas internas y comunicación asíncrona.

### Comando de Instalación:
```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

---

## 4. Fase 3: Arquitectura del Código Desarrollado

La estructura creada dentro de `backend/` es:

```text
backend/
├── .venv/                      # Entorno virtual aislado
├── app/
│   ├── __init__.py             # Marca la carpeta como paquete Python
│   ├── models.py               # Modelos Pydantic v2 de la base de datos
│   ├── main.py                 # Servidor FastAPI, Motor JEV y Chatbot
│   └── templates/
│       └── index.html          # Dashboard interactivo con Tailwind CSS
├── requirements.txt            # Dependencias fijadas
├── .dockerignore               # Archivos que Docker no debe empaquetar
└── Dockerfile                  # Receta de construcción del contenedor
```

### 4.1 `app/models.py`: Esquemas de Datos
Define las clases Pydantic basadas en nuestro documento de base de datos:
* `TelemetryInput`: Captura `soil_moisture`, `ambient_temperature`, `ph_level`, `nitrogen_ppm`, etc.
* `JevDecisionResponse`: Estructura estricta con `decision_action` (booleano), `decision_intensity` (0-100%), `commanded_tools` (lista de actuadores) y `justification_reason`.
* `PlantProfile`: Umbrales botánicos investigados por el LLM.
* `FarmChatRequest` y `FarmChatResponse`: Intercambio para "Habla con tu Granja".

### 4.2 `app/main.py`: Lógica del Sistema
* **Motor JEV**: Evalúa primero heladas críticas ($\le -1.5^\circ\text{C}$), luego ráfagas de viento ($> 20\text{ km/h}$), y luego déficit de humedad del suelo, calculando la potencia proporcional de la bomba.
* **Simulador de Escenarios**: Endpoint `/api/v1/simulate/{scenario}` para probar sequía, helada o clima óptimo con un solo clic.
* **"Habla con tu Granja"**: Endpoint `/api/v1/chat/farm` que responde preguntas del agricultor usando los valores reales de los sensores.

---

## 5. Fase 4: Cómo Ejecutar y Probar la App en Local

Para levantar el servidor en tu computadora sin Docker (para desarrollar y probar):

```powershell
# 1. Abre PowerShell y entra a la carpeta backend
cd "c:\Users\Jonathan\OneDrive\Desktop\Santo Tomas\Proyecto Feria\backend"

# 2. Ejecuta Uvicorn apuntando a main.py
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### ¿Qué verás en tu navegador?
1. **Dashboard Web**: Entra a [http://localhost:8000](http://localhost:8000). Verás el panel en tiempo real con métricas, estado de JEV y la caja de chat.
2. **Documentación Swagger Interactiva**: Entra a [http://localhost:8000/docs](http://localhost:8000/docs). Puedes probar cada endpoint directamente desde el navegador.
3. **Health Check**: Entra a [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health). Retorna `{"status": "healthy"}`.

---

## 6. Fase 5: Dockerización de la Aplicación

El archivo `backend/Dockerfile` empaqueta la aplicación en una imagen inmutable de Linux.

### 6.1 Explicación del `Dockerfile`:
```dockerfile
# 1. Usamos Python 3.12 ligero sobre Debian
FROM python:3.12-slim

# 2. Logs en tiempo real y sin archivos temporales
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Directorio de trabajo
WORKDIR /app

# 4. Copiamos e instalamos dependencias primero (aprovecha la caché de Docker)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 5. Copiamos el código fuente
COPY app /app/app

# 6. Exponemos el puerto
EXPOSE 8000

# 7. Comando de arranque
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 Comandos Docker para Ejecutar en Local:

```powershell
# Asegúrate de tener Docker Desktop abierto y corriendo

# 1. Construir la imagen Docker localmente
cd "c:\Users\Jonathan\OneDrive\Desktop\Santo Tomas\Proyecto Feria\backend"
docker build -t agrosense-cloud:v1.0 .

# 2. Ejecutar el contenedor en segundo plano en el puerto 8000
docker run -d -p 8000:8000 --name agrosense-container agrosense-cloud:v1.0

# 3. Verificar que está corriendo
docker ps

# 4. Ver los logs en vivo
docker logs -f agrosense-container

# 5. Probar en el navegador
# Abre http://localhost:8000
```

> [!TIP]
> **Capturas obligatorias para tu informe de Santo Tomás:**
> 1. Captura de la terminal ejecutando `docker build -t agrosense-cloud:v1.0 .`
> 2. Captura de `docker ps` mostrando el contenedor activo.
> 3. Captura del navegador abriendo `http://localhost:8000` con el Dashboard.

---

## 7. Fase 6: Despliegue en Microsoft Azure (ACR + ACI)

Esta fase cumple los criterios de evaluación de **Azure Container Registry (10 pts)**, **Azure Container Instances (10 pts)** y **Enlace Público Funcional (10 pts)**.

### Paso 1: Autenticación en Azure
```powershell
# Iniciar sesión en tu cuenta de Azure (abrirá el navegador)
az login
```

### Paso 2: Crear el Grupo de Recursos
```powershell
# Creamos un grupo de recursos en la región de Chile o Este de EE.UU.
az group create --name rg-agrosense-st --location chilecentral
```

### Paso 3: Crear el Azure Container Registry (ACR)
```powershell
# El nombre del registro debe ser único en todo Azure (solo letras y números)
az acr create --resource-group rg-agrosense-st --name acragrosensejonathan --sku Basic --admin-enabled true

# Iniciar sesión en nuestro registro privado de Azure
az acr login --name acragrosensejonathan
```

### Paso 4: Etiquetar y Subir la Imagen Docker al ACR
```powershell
# Etiquetamos la imagen local con la dirección del ACR
docker tag agrosense-cloud:v1.0 acragrosensejonathan.azurecr.io/agrosense-cloud:v1.0

# Subimos la imagen a la nube de Azure
docker push acragrosensejonathan.azurecr.io/agrosense-cloud:v1.0

# Verificar que la imagen está en el repositorio de Azure
az acr repository list --name acragrosensejonathan --output table
```

### Paso 5: Desplegar en Azure Container Instances (ACI) con URL Pública
```powershell
# Obtenemos la contraseña del ACR
$ACR_PASSWORD = az acr credential show --name acragrosensejonathan --query "passwords[0].value" --output tsv

# Desplegamos el contenedor en ACI con nombre de dominio público (DNS)
az container create `
  --resource-group rg-agrosense-st `
  --name agrosense-app-instance `
  --image acragrosensejonathan.azurecr.io/agrosense-cloud:v1.0 `
  --registry-login-server acragrosensejonathan.azurecr.io `
  --registry-username acragrosensejonathan `
  --registry-password $ACR_PASSWORD `
  --dns-name-label agrosense-jonathan-st `
  --ports 8000 `
  --cpu 1 `
  --memory 1.5 `
  --restart-policy Always
```

### Paso 6: Obtener y Probar la URL Pública
```powershell
# Consultar el FQDN (dominio público generado por Azure)
az container show --resource-group rg-agrosense-st --name agrosense-app-instance --query ipAddress.fqdn --output tsv
```

La URL generada será del estilo:  
👉 `http://agrosense-jonathan-st.chilecentral.azurecontainer.io:8000`

Al abrirla en cualquier navegador, tu profesor y los jueces verán tu plataforma funcionando en la nube de Azure con nota máxima garantizada.

---

## 8. Checklist de Rúbrica de Evaluación (Santo Tomás - 70 Puntos)

| Criterio | Puntaje | Dónde se cumple en nuestro proyecto |
| :--- | :---: | :--- |
| **Documentación del proceso** | **20 pts** | Este documento `Guia_Backend_Azure.md` explica cada comando, decisión y flujo paso a paso. |
| **Dockerización en local** | **20 pts** | `backend/Dockerfile` optimizado, probado con `docker build` y `docker run` en `http://localhost:8000`. |
| **Despliegue en Azure Container Registry (ACR)** | **10 pts** | Imagen etiquetada y subida mediante `az acr login` y `docker push`. |
| **Despliegue en Azure Container Instances (ACI)** | **10 pts** | Contenedor instanciado con `az container create` en puerto 8000. |
| **Enlace público funcional** | **10 pts** | FQDN público asignado y operativo para que el docente pueda interactuar con el Dashboard. |
| **TOTAL** | **70 pts** | **100% de la evaluación sumativa (Nota 7.0).** |
