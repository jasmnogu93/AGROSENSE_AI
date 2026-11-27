# Política de Seguridad

## Manejo de Secretos y Credenciales

- Este repositorio **no** almacena credenciales reales, archivos `.env`, tokens de API ni claves privadas.
- Toda configuración sensible debe definirse localmente en `backend/.env` (ignorado por Git), tomando como plantilla [`backend/.env.example`](backend/.env.example).
- Los sketches de firmware usan marcadores genéricos (`TU_WIFI_2_4GHZ`, `TU_PASSWORD_WIFI`) en lugar de credenciales de red reales.

## Alcance del Prototipo vs. Producción

En su etapa actual de MVP académico/demostrativo, el proyecto se conecta a un broker MQTT público (`broker.emqx.io:1883`) sin autenticación de dispositivo y mantiene políticas permisivas de demo. Antes de un despliegue productivo se contempla:

1. Migración a **MQTT sobre TLS (puerto 8883)** con credenciales por dispositivo.
2. Activación de **Row Level Security (RLS)** en Supabase PostgreSQL y rotación periódica de llaves.
3. Autenticación mediante **JWT / OAuth2** en las rutas de escritura de la API REST.

## Reporte de Vulnerabilidades

Si detectas algún problema de seguridad o fuga accidental de información, por favor repórtalo de forma privada a través de un issue de seguridad o contacto directo con el mantenedor antes de divulgar detalles públicamente.
