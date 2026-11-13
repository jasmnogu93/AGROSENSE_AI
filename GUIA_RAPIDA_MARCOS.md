# Guía Rápida para Marcos — AgroSense AI (`AgroFieldService` / Integración II)

> **Colaborador verificado en GitHub:** `nacomantesmurf` (Marcos Bustos — permiso `write`)  
> **Repositorio oficial:** `https://github.com/jasmnogu93/AGROSENSE_AI.git`  
> **Tu rama de trabajo asignada:** `MarcosRama`  
> **Tu foco principal:** Servicio 1 (`AgroFieldService` — Invernadero de Orquídeas, **Integración de Competencias II `IEI-094`**, RF1–RF7)

---

## 1. Cómo descargar el proyecto en tu PC

Abre una terminal (**PowerShell** o **Git Bash**) en tu Escritorio (evita meter código ni `.venv` dentro de OneDrive) y ejecuta:

### Si es la primera vez que descargas el repo:
```bash
git clone -b MarcosRama https://github.com/jasmnogu93/AGROSENSE_AI.git
cd AGROSENSE_AI
```

### Si ya habías clonado el repo antes:
```bash
cd AGROSENSE_AI
git fetch origin
git checkout MarcosRama
git pull origin MarcosRama
```

---

## 2. Cómo instalar y levantar el Backend + Dashboard Web (`FastAPI` + `SQLite`)

Requiere **Python 3.10+** instalado. Desde la carpeta raíz `AGROSENSE_AI` en **PowerShell**:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

> **Tip en Windows:** Si PowerShell bloquea `Activate.ps1` por permisos de ejecución, puedes ejecutar directo sin activar el script:  
> `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`  
> `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

Una vez encendido, abre en tu navegador:
* **Dashboard Web (3 servicios, selecciona la pestaña Orquídeas):** `http://localhost:8000`
* **Swagger UI (para probar cada endpoint sin programar aún):** `http://localhost:8000/docs`

---

## 3. Cómo verificar que todo funciona (`pytest`)

En otra terminal (desde la raíz `AGROSENSE_AI`), ejecuta la suite automática (usa una BD temporal aislada y no daña tus datos locales):

```powershell
Push-Location backend; .\.venv\Scripts\python.exe -m pytest tests/test_api.py -v; Pop-Location
```

Debe mostrar **7 tests pasando** (`7 passed`).

---

## 4. Qué archivos y endpoints te corresponden (Caso Orquídeas — `IEI-094`)

Para no mezclar ramos, el proyecto separa 3 servicios independientes:
* **`AgroFieldService` (Tuyo — Integración II `IEI-094`):** Orquídeas (*Phalaenopsis sp.*), objetivo 80% humedad relativa (75–85%), 18–24 °C, calendario semanal `Lun..Dom` + hora.
* **`HomeTowerService` (Jonathan y Miguel — Feria / IoT / Android):** Mini Torre Hidropónica (`ASAIapp/` + `firmware/`). No necesitas modificar estas carpetas.

### Documentación y código clave para revisar:
* **Especificación funcional (RF1–RF7):** [`specs/spec-002-field-greenhouse-service.md`](specs/spec-002-field-greenhouse-service.md)
* **Router de Orquídeas:** [`backend/app/routers/field_service.py`](backend/app/routers/field_service.py)
* **Persistencia SQLite:** [`backend/app/db.py`](backend/app/db.py) (tablas `calendario_semanal`, `estado_modulo`, `telemetria_historica` en `backend/agrosense.db`)

### Endpoints REST listos para consumir desde Web o tu App Android de Orquídeas:
*(Si consumes desde un celular físico o emulador Android en tu red local, reemplaza `localhost` por la IP de tu PC en Wi-Fi, o `10.0.2.2` en el emulador).*

| Método y Ruta | Para qué sirve | Ejemplo de Body JSON (cuando aplica) |
| :--- | :--- | :--- |
| `GET /api/v1/services/field/status` | Estado actual del invernadero de orquídeas, perfil 80% HR / 18–24 °C, calendario, notificación y alertas (RF4, RF7). | *(Sin body)* |
| `GET /api/v1/services/field/schedule` | Consultar días activos y hora programada de riego (RF1). | *(Sin body)* |
| `POST /api/v1/services/field/schedule` | Guardar calendario semanal en SQLite (RF1). | `{"active_days": ["Lun", "Mié", "Vie"], "irrigation_time": "08:30", "duration_minutes": 20}` |
| `GET /api/v1/services/field/notification` | Obtener el mensaje de próximo riego programado (RF2). | *(Sin body)* |
| `POST /api/v1/services/field/telemetry` | Enviar lectura de sensores de temperatura/humedad vía Wi-Fi (RF3, RF5, RF6). | `{"air_temperature": 21.5, "air_humidity": 80.0, "soil_humidity_pct": 68.0}` |
| `GET /api/v1/services/field/history?limit=10` | Consultar histórico almacenado en SQLite (RF5). | *(Sin body)* |

*(Nota: Los días válidos en `active_days` incluyen tilde en miércoles y sábado: `"Lun"`, `"Mar"`, `"Mié"`, `"Jue"`, `"Vie"`, `"Sáb"`, `"Dom"`).*

---

## 5. Cómo guardar y subir tus avances a tu rama (`MarcosRama`)

Trabaja siempre dentro de `MarcosRama` para no pisar `main` ni `MiguelRama`. Cuando hagas cambios o agregues archivos de tu parte:

```bash
# 1. Asegúrate de estar en tu rama y actualizado
git checkout MarcosRama
git pull origin MarcosRama

# 2. Revisa qué archivos cambiaste (nunca subas .venv ni *.db; .gitignore ya los bloquea)
git status

# 3. Guarda y sube tus cambios
git add .
git commit -m "feat(orquideas): descripcion corta de tu avance"
git push origin MarcosRama
```

---

## Checklist rápido si algo falla
1. **Error `ModuleNotFoundError` al correr `pytest` o `uvicorn`:** Asegúrate de ejecutarlos usando `.\.venv\Scripts\python.exe -m ...` dentro de la carpeta `backend/`.
2. **Error `Address already in use` en puerto `8000`:** Ya hay otra terminal corriendo Uvicorn, o cambia a `--port 8001`.
3. **Al hacer `git push` pide clave:** Inicia sesión en GitHub con tu cuenta `nacomantesmurf` (en Windows Git Credential Manager abre ventana del navegador para autorizar).
