# ==============================================================================
# Dockerfile para AgroSense AI - Backend Cloud (FastAPI)
# Diseñado para Microsoft Azure Container Instances (ACI) y Azure Container Registry (ACR)
# ==============================================================================

# 1. Imagen base oficial de Python ligera basada en Debian Linux
FROM python:3.12-slim

# 2. Variables de entorno para optimizar la ejecución en contenedores
# - PYTHONDONTWRITEBYTECODE: evita generar archivos .pyc en disco
# - PYTHONUNBUFFERED: asegura que los logs salgan inmediatamente a la consola de Azure
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Copiar primero el archivo de dependencias para aprovechar el caché de Docker
COPY requirements.txt /app/requirements.txt

# 5. Instalar dependencias sin guardar caché temporal para mantener la imagen liviana
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# 6. Copiar el código fuente de la aplicación dentro del contenedor
COPY app /app/app

# 7. Exponer el puerto de red en el que escuchará FastAPI
EXPOSE 8000

# 8. Comando de arranque del servidor ASGI Uvicorn
# Se enlaza a 0.0.0.0 para aceptar tráfico externo desde Azure o la red local
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
