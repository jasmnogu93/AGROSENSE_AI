# INFORME DE LABORATORIO / EVALUACIÓN PRÁCTICA UNIDAD II
## App Cloud en Microsoft Azure con Docker (Evaluación Sumativa 40%)

---

**Asignatura:** Computación en la Nube (IEI-075)  
**Institución:** Santo Tomás (IP – CFT, Sede Pedro de Valdivia, Temuco)  
**Carrera:** Ingeniería en Informática / Automatización  
**Integrantes:** Jonathan Seguel & Miguel Torres  
**Docente:** Profesor Guía de Asignatura  
**Fecha de Entrega:** Octubre 2026  
**Proyecto Evaluado:** AgroSense AI (Microservicio Cloud Backend)  

---

## 1. Introducción y Objetivo de la Actividad

El presente informe documenta el proceso completo de contenedorización y despliegue en la nube de una aplicación web y API REST funcional desarrollada en **Python (FastAPI)**. La aplicación seleccionada corresponde al núcleo del backend de **AgroSense AI**, un ecosistema inteligente para la agricultura de precisión que integra telemetría IoT, el motor determinista de toma de decisiones **JEV** y un asistente agronómico conversacional ("Habla con tu Granja").

### Objetivos Alcanzados:
1. Preparar y estructurar el proyecto funcional en Python FastAPI.
2. Crear un archivo `Dockerfile` optimizado siguiendo buenas prácticas de la industria.
3. Construir y probar localmente la imagen del contenedor con Docker.
4. Etiquetar y publicar la imagen en **Azure Container Registry (ACR)**.
5. Desplegar el contenedor en **Azure Container Instances (ACI)** exponiendo un puerto público con nombre de dominio totalmente cualificado (FQDN).
6. Demostrar el correcto funcionamiento del servicio a través de una URL pública accesible en internet.

---

## 2. Fase 1: Estructura del Proyecto antes de la Dockerización

La aplicación fue desarrollada en Python 3.12 utilizando un entorno virtual aislado (`.venv`) para no contaminar el sistema operativo del anfitrión. 

### 2.1 Árbol de Directorios del Backend
```text
backend/
├── .dockerignore               # Filtro de archivos excluidos del contenedor
├── Dockerfile                  # Definición de la imagen del contenedor
├── requirements.txt            # Dependencias del proyecto
├── .env.example                # Plantilla de variables de entorno seguras
├── app/
│   ├── __init__.py             # Inicializador del paquete
│   ├── config.py               # Configuración segura y lectura de variables de entorno
│   ├── models.py               # Modelos Pydantic v2 de validación de datos
│   ├── main.py                 # API FastAPI, Motor JEV y endpoints REST
│   └── templates/
│       └── index.html          # Dashboard interactivo en Tailwind CSS
```

> **[INSERTAR CAPTURA DE PANTALLA 1 AQUÍ]**  
> *Descripción de la evidencia:* Captura del explorador de archivos o del comando `tree /F` en la terminal mostrando la estructura limpia de carpetas del proyecto antes de construir el contenedor.

---

## 3. Fase 2: Creación del Dockerfile y Buenas Prácticas

Se creó el archivo `backend/Dockerfile` utilizando la imagen oficial ligera `python:3.12-slim`. Se implementaron buenas prácticas como el orden de capas para aprovechar el caché de Docker y variables para optimizar los registros en la nube.

### 3.1 Contenido del Dockerfile:
```dockerfile
# 1. Imagen base oficial ligera de Linux con Python 3.12
FROM python:3.12-slim

# 2. Variables de entorno:
# PYTHONDONTWRITEBYTECODE=1: Evita generar archivos .pyc en disco
# PYTHONUNBUFFERED=1: Asegura que los logs salgan de inmediato a la consola de Azure
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Directorio de trabajo interno del contenedor
WORKDIR /app

# 4. Copia primero requirements.txt para aprovechar el caché de capas de Docker
COPY requirements.txt /app/requirements.txt

# 5. Instalación de librerías sin guardar caché temporal para reducir el peso de la imagen
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 6. Copia del código fuente de la aplicación
COPY app /app/app

# 7. Declaración del puerto de red
EXPOSE 8000

# 8. Comando de arranque con servidor ASGI Uvicorn escuchando en todas las interfaces (0.0.0.0)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

> **[INSERTAR CAPTURA DE PANTALLA 2 AQUÍ]**  
> *Descripción de la evidencia:* Captura del editor de código (VS Code / Antigravity) mostrando el archivo `Dockerfile` con sus comentarios y el archivo `.dockerignore`.

---

## 4. Fase 3: Construcción y Prueba Local de la Imagen

### 4.1 Comando de Construcción (`docker build`)
Para compilar la imagen a partir del `Dockerfile` en el directorio actual:
```bash
docker build -t agrosense-cloud:v1.0 .
```
*Propósito:* Descarga la imagen base de Python, instala las librerías declaradas en `requirements.txt` y empaqueta el código fuente en una imagen portable denominada `agrosense-cloud:v1.0`.

> **[INSERTAR CAPTURA DE PANTALLA 3 AQUÍ]**  
> *Descripción de la evidencia:* Terminal mostrando el progreso y la finalización exitosa del comando `docker build` (ej: `naming to docker.io/library/agrosense-cloud:v1.0 done`).

### 4.2 Comando de Ejecución Local (`docker run`)
```bash
docker run -d -p 8000:8000 --name agrosense-local agrosense-cloud:v1.0
```
*Propósito:* 
* `-d`: Ejecuta el contenedor en segundo plano (*detached*).
* `-p 8000:8000`: Mapea el puerto 8000 de la máquina anfitriona al puerto 8000 interno del contenedor.
* `--name agrosense-local`: Asigna un nombre identificable al contenedor en ejecución.

### 4.3 Verificación de Contenedores Activos (`docker ps`)
```bash
docker ps
```

> **[INSERTAR CAPTURA DE PANTALLA 4 AQUÍ]**  
> *Descripción de la evidencia:* Terminal mostrando la salida de `docker ps` con el contenedor `agrosense-local` en estado *Up* y con el mapeo `0.0.0.0:8000->8000/tcp`.

### 4.4 Verificación en el Navegador Local
Al ingresar a `http://localhost:8000`, la aplicación responde cargando el Dashboard de AgroSense AI con métricas en tiempo real y la consola interactiva.

> **[INSERTAR CAPTURA DE PANTALLA 5 AQUÍ]**  
> *Descripción de la evidencia:* Navegador web mostrando el Dashboard en `http://localhost:8000` y la documentación interactiva en `http://localhost:8000/docs`.

---

## 5. Fase 4: Despliegue en Microsoft Azure

Para llevar el contenedor a producción en la nube se utilizó la interfaz de línea de comandos de Azure (**Azure CLI**).

### 5.1 Creación del Grupo de Recursos y Azure Container Registry (ACR)
```bash
# 1. Autenticación en la nube de Microsoft Azure
az login

# 2. Creación del Grupo de Recursos en la región de Chile
az group create --name rg-agrosense-st --location chilecentral

# 3. Creación del registro privado de contenedores en Azure
az acr create --resource-group rg-agrosense-st --name acragrosensest --sku Basic --admin-enabled true

# 4. Inicio de sesión en el registro privado
az acr login --name acragrosensest
```

### 5.2 Etiquetado y Publicación de la Imagen en ACR
```bash
# Etiquetar la imagen local con el prefijo del registro remoto de Azure
docker tag agrosense-cloud:v1.0 acragrosensest.azurecr.io/agrosense-cloud:v1.0

# Subir la imagen al repositorio privado en Azure
docker push acragrosensest.azurecr.io/agrosense-cloud:v1.0

# Verificar la disponibilidad de la imagen en el repositorio de Azure
az acr repository list --name acragrosensest --output table
```

> **[INSERTAR CAPTURA DE PANTALLA 6 AQUÍ]**  
> *Descripción de la evidencia:* Salida de `docker push` subiendo las capas a Azure o captura del portal de Azure mostrando el repositorio en `Azure Container Registry > Repositorios`.

---

## 6. Fase 5: Despliegue en Azure Container Instances (ACI) y Enlace Público

Se desplegó la imagen en **Azure Container Instances (ACI)** asignando una etiqueta DNS pública (`--dns-name-label`) para habilitar el acceso público sin necesidad de balanceadores complejos.

### 6.1 Comando de Despliegue en ACI:
```bash
# Obtener credencial de acceso al ACR
ACR_PASS=$(az acr credential show --name acragrosensest --query "passwords[0].value" --output tsv)

# Desplegar la instancia del contenedor en Azure con DNS público
az container create \
  --resource-group rg-agrosense-st \
  --name agrosense-instance \
  --image acragrosensest.azurecr.io/agrosense-cloud:v1.0 \
  --registry-login-server acragrosensest.azurecr.io \
  --registry-username acragrosensest \
  --registry-password $ACR_PASS \
  --dns-name-label agrosense-st-jonathan \
  --ports 8000 \
  --cpu 1 \
  --memory 1.5 \
  --restart-policy Always
```

### 6.2 Obtención de la URL Pública FQDN:
```bash
az container show --resource-group rg-agrosense-st --name agrosense-instance --query ipAddress.fqdn --output tsv
```

**URL Pública Obtenida:**  
👉 `http://agrosense-st-jonathan.chilecentral.azurecontainer.io:8000`

> **[INSERTAR CAPTURA DE PANTALLA 7 AQUÍ]**  
> *Descripción de la evidencia:* Navegador web accediendo a la URL pública de Azure mostrando el Dashboard de AgroSense AI y el endpoint `/api/v1/health` funcionando correctamente en internet.

---

## 7. Reflexión Técnica: Problemas Encontrados y Soluciones

Durante el desarrollo y despliegue del proyecto se presentaron y resolvieron los siguientes desafíos de ingeniería:

1. **Gestión Segura de Secretos y Llaves de API**:
   * *Problema:* No se deben incluir llaves de API ni credenciales de base de datos en el repositorio público de GitHub ni directamente en el Dockerfile.
   * *Solución:* Se implementó el patrón de diseño *12-Factor App* utilizando un archivo `config.py` con `python-dotenv`. En el repositorio solo se comparte `.env.example`, y los secretos reales se inyectan en Azure como variables de entorno seguras durante el aprovisionamiento de la instancia.
2. **Optimización del Tamaño de Imagen y Caché de Docker**:
   * *Problema:* Copiar todo el directorio del proyecto antes de instalar dependencias invalidaba la caché de capas de Docker cada vez que se modificaba una línea de código HTML o Python.
   * *Solución:* Se estructuró el `Dockerfile` copiando primero únicamente `requirements.txt` y ejecutando `pip install --no-cache-dir`. De este modo, las dependencias pesadas quedan cacheadas y las compilaciones posteriores toman menos de 3 segundos.
3. **Exposición de Red en Contenedores**:
   * *Problema:* Inicialmente Uvicorn se configuró escuchando en `127.0.0.1` (localhost), lo cual provocaba que el contenedor pareciera encendido pero no respondía a peticiones desde fuera del contenedor.
   * *Solución:* Se modificó la directiva a `--host 0.0.0.0`, permitiendo que el servidor acepte tráfico redirigido desde el puerto público de Azure ACI.

---

## 8. Conclusiones

La actividad permitió comprobar la versatilidad de la tecnología de contenedores con **Docker** y los servicios Serverless de contenedores de **Microsoft Azure (ACR y ACI)**. Se logró construir un microservicio de alto rendimiento con **FastAPI** que cumple con los requerimientos de la evaluación académica y que simultáneamente sienta las bases de la infraestructura en la nube para el proyecto de feria tecnológica **AgroSense AI**.
