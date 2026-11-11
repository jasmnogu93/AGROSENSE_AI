# SPEC-006: Motor Ciberfísico (JEV), Chat Agronómico y Simulación de Escenarios

> **Documento:** `specs/spec-006-ai-and-simulation.md`  
> **Estado:** APROBADO  
> **Implementación Actual:** `backend/app/main.py` (`evaluate_jev_local`, `evaluate_jev`, `simulate_scenario`, `chat_with_farm`)  
> **Autor:** `architect` & `spec_lead`

---

## 1. Principio Inviolable de Seguridad Ciberfísica
> **Regla de Oro:** La protección física del hardware (bloqueo de bomba sumergible 5V por estanque seco y alivio térmico crítico) **NUNCA depende de un LLM, de MCP, de LangGraph ni de conexión a internet**. Toda protección crítica se ejecuta mediante lógica determinista local en el ESP32 y en `evaluate_jev_local()`.

---

## 2. Motor de Decisión Rápida (JEV + Fallback Determinista)

### 2.1. Reglas Deterministas Locales (`evaluate_jev_local`)
Evaluadas en orden de prioridad estricta sobre `TelemetryInput` y `PlantProfile`:
1. **Regla Crítica — Protección Anti-Cavitación:**
   * **Condición:** `reservoir_level_percent < 20.0`
   * **Salida:** `risk_level = "CRITICAL"`, `action_required = True`, `recommended_pump_state = False`, `fallback_rule_applied = True`.
2. **Regla Térmica / Transpiración — Alivio Cenital Servo SG90:**
   * **Condición:** `air_temperature > optimal_temp_max_c` **o** `vpd_kpa > optimal_vpd_max_kpa` (con cálculo previo de Tetens si `vpd_kpa` es `None`).
   * **Salida:** `risk_level = "WARNING"`, `action_required = True`, `recommended_vent_angle = 90`, `fallback_rule_applied = True`.
3. **Estado Óptimo:**
   * **Salida:** `risk_level = "NORMAL"`, `action_required = False`, `recommended_vent_angle = 0`.

### 2.2. Inferencia en la Nube (`evaluate_jev` — Plug-and-Play)
* Si `settings.LLM_API_KEY` está configurada (distinta de vacío, `"tu_api_key_aqui"` o `"dev_local_key*"`), consulta vía HTTP POST (`timeout=8.0s`) a `settings.JEV_DECISIONS_API_URL` (`typesafe/jev-latest`).
* Ante cualquier error HTTP o de red, conmuta transparentemente a `evaluate_jev_local` anteponiendo un aviso en `reason`.

### 2.3. Contrato `JevDecisionResponse`
```json
{
  "action_required": true,
  "recommended_pump_state": false,
  "recommended_vent_angle": 90,
  "reason": "...",
  "risk_level": "NORMAL | WARNING | CRITICAL",
  "execution_time_ms": 12.0,
  "fallback_rule_applied": true,
  "executed_at": "2026-11-11T19:00:00Z"
}
```

---

## 3. Simulador de Escenarios (`POST /api/v1/simulate/{scenario}`)
Permite probar en vivo las reacciones ciberfísicas y registrar telemetría en SQLite sin esperar a los sensores físicos:

| Parámetro `scenario` | Efecto sobre `latest_telemetry` | Reacción Esperada de `evaluate_jev` |
| :--- | :--- | :--- |
| `estanque_vacio` | `reservoir_level_percent = 12.0`, `pump_active = False` | `risk_level = "CRITICAL"`, bloqueo de bomba |
| `calor_extremo` | `air_temperature = 28.5`, `air_humidity = 42.0`, recalcula DPV | `risk_level = "WARNING"`, `recommended_vent_angle = 90` |
| `optimo` | `reservoir_level_percent = 85.0`, `air_temperature = 21.5`, `air_humidity = 62.0`, `vpd_kpa = 0.95`, `vent_servo_angle = 0` | `risk_level = "NORMAL"` |
| `recirculacion` | `reservoir_level_percent = 80.0`, `pump_active = True` | `risk_level = "NORMAL"`, bomba activa |
| *Otro valor* | — | Responde **HTTP 400** (`Escenario no reconocido.`) |

---

## 4. Asistente Agronómico Conversacional (`POST /api/v1/chat/farm`)
* **Request (`FarmChatRequest`):** `{ "question": "...", "session_id": "session_01", "include_live_telemetry": true }`
* **Modo Nube (DeepSeek / OpenAI-compatible):** Inyecta el estado actual (cultivo, rangos óptimos, última telemetría y decisión JEV) en el `system_prompt` y llama a `{LLM_BASE_URL}/chat/completions` (`model = settings.LLM_MODEL_NAME`, `temperature = 0.3`, `max_tokens = 400`, `timeout = 20.0s`).
* **Modo Local Heurístico (Fallback sin clave o fallo de red):** Analiza palabras clave en `question`:
  * `"bomba" | "riego" | "estanque" | "calendario"` → informa nivel, estado de bomba, programación y `latest_jev_decision.reason`.
  * `"temperatura" | "humedad" | "clima" | "dpv"` → informa temperatura, humedad, DPV y ángulo del servo.
  * *Otras consultas* → resumen general del módulo y persistencia SQLite (`model_used = "local-heuristics"`).

---

## 5. Evolución Fase 2 (Opcional — Solo tras cerrar ESP32 + Android)
* **MCP (Model Context Protocol):** Exponer herramientas de solo lectura y calendario (`get_telemetry_history`, `get_field_schedule`) para que el asistente no dependa únicamente de inyección estática en el prompt.
* **LangGraph:** Introducir un grafo con estado únicamente si se requiere un agente multi-paso con **confirmación humana obligatoria (*human-in-the-loop*)** antes de ejecutar comandos sobre actuadores.
