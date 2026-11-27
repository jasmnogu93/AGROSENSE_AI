# ==============================================================================
# AGROSENSE AI — PUENTE MQTT BIDIRECCIONAL (ESP32 <-> FASTAPI <-> ANDROID)
# ==============================================================================
# Conecta el backend de AgroSense con el broker MQTT (broker.emqx.io:1883).
# Suscribe a telemetría de la Mini Torre ('celda-01') y publica comandos manuales.
# ==============================================================================

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from app import db
from app.config import settings

logger = logging.getLogger("asai.mqtt_bridge")

SUBSCRIBED_TOPICS = [
    ("ASAI/Temperatura", 0),
    ("ASAI/Humedad", 0),
    ("ASAI/Exterior/Temperatura", 0),
    ("ASAI/Exterior/Humedad", 0),
    ("ASAI/Nivel", 0),
    ("ASAI/DPV", 0),
    ("ASAI/Presion", 0),
    ("ASAI/Bomba", 0),
    ("ASAI/Servo", 0),
    ("ASAI/Alerta", 0),
    # Tópicos aislados para simulación Wokwi / ESP32 de Orquídeas (IEI-094)
    ("ASAI/Orquideas/Temperatura", 0),
    ("ASAI/Orquideas/Humedad", 0),
    ("ASAI/Orquideas/Sustrato", 0),
    ("ASAI/Orquideas/Presion", 0),
    ("ASAI/Orquideas/Bomba", 0),
]


class MqttBridgeService:
    """
    Servicio de puente MQTT bidireccional no bloqueante.
    Mantiene sincronizado el estado persistente ('celda-01' e 'invernadero-orquideas') con ESP32/Wokwi.
    """

    def __init__(self) -> None:
        self.client_id: str = f"{settings.MQTT_CLIENT_ID_PREFIX}{uuid.uuid4().hex[:8]}"
        self.last_message_at: Optional[str] = None
        self.last_field_message_at: Optional[str] = None
        self.last_alert: Optional[str] = None
        self._client: Optional[mqtt.Client] = None
        self._connected: bool = False
        self._last_telemetry_insert_time: float = 0.0
        self._last_field_insert_time: float = 0.0
        self._last_pump_active: Optional[bool] = None
        self._last_servo_angle: Optional[int] = None

    def start(self) -> None:
        """Inicia el cliente MQTT en un hilo de fondo (loop_start)."""
        if not settings.MQTT_ENABLED:
            logger.info("MQTT_ENABLED=False. Puente MQTT no iniciado.")
            return

        if self._client is not None:
            return

        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
            )
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            self._client = client

            client.connect_async(
                settings.MQTT_BROKER_HOST,
                settings.MQTT_BROKER_PORT,
                keepalive=60,
            )
            client.loop_start()
            logger.info(
                f"Puente MQTT conectando a {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT} "
                f"(client_id={self.client_id})"
            )
        except Exception as e:
            logger.error(f"Fallo al conectar el puente MQTT: {e}")
            self._client = None
            self._connected = False

    def stop(self) -> None:
        """Detiene el bucle de red y desconecta el cliente MQTT."""
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception as e:
                logger.warning(f"Error al desconectar cliente MQTT: {e}")
            finally:
                self._client = None
                self._connected = False

    def get_status(self) -> Dict[str, Any]:
        """Retorna el estado de conexión y diagnóstico del puente MQTT."""
        return {
            "enabled": bool(settings.MQTT_ENABLED),
            "connected": bool(self._connected),
            "broker": settings.MQTT_BROKER_HOST,
            "port": int(settings.MQTT_BROKER_PORT),
            "client_id": self.client_id,
            "last_message_at": self.last_message_at,
            "last_field_message_at": self.last_field_message_at,
            "last_alert": self.last_alert,
        }

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties) -> None:
        if reason_code == 0:
            self._connected = True
            logger.info(f"Puente MQTT conectado exitosamente al broker {settings.MQTT_BROKER_HOST}")
            client.subscribe(SUBSCRIBED_TOPICS)
        else:
            self._connected = False
            logger.warning(f"Fallo de conexión MQTT. Código de razón: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self._connected = False
        logger.info(f"Puente MQTT desconectado del broker (código {reason_code})")

    def _on_message(self, client, userdata, message) -> None:
        try:
            topic = message.topic
            payload = message.payload.decode("utf-8", errors="ignore")
            self.handle_message(topic, payload)
        except Exception as e:
            logger.error(f"Excepción no controlada en _on_message ({message.topic}): {e}")

    def handle_message(self, topic: str, payload: str) -> None:
        """
        Procesa de forma segura una publicación MQTT entrante sin propagar excepciones.
        Actualiza estado_modulo ('celda-01') e inserta telemetría con throttle.
        """
        try:
            norm_topic = topic.strip().lstrip("/")
            payload_str = payload.strip()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.last_message_at = now_str

            # Rama aislada para Orquídeas (IEI-094 / Wokwi por MQTT)
            if norm_topic.startswith("ASAI/Orquideas/"):
                field_updates: Dict[str, Any] = {}
                if norm_topic == "ASAI/Orquideas/Temperatura":
                    field_updates["air_temperature"] = float(payload_str)
                elif norm_topic == "ASAI/Orquideas/Humedad":
                    field_updates["air_humidity"] = float(payload_str)
                elif norm_topic == "ASAI/Orquideas/Sustrato":
                    field_updates["soil_humidity_pct"] = float(payload_str)
                elif norm_topic == "ASAI/Orquideas/Presion":
                    field_updates["barometric_pressure_hpa"] = float(payload_str)
                elif norm_topic == "ASAI/Orquideas/Bomba":
                    b_up = payload_str.upper()
                    if b_up in ("ON", "1", "TRUE"):
                        field_updates["pump_active"] = True
                    elif b_up in ("OFF", "0", "FALSE"):
                        field_updates["pump_active"] = False
                else:
                    return

                self.last_field_message_at = now_str
                st_field = db.save_module_state("invernadero-orquideas", **field_updates)
                if any(k in field_updates for k in ("air_temperature", "air_humidity", "soil_humidity_pct", "barometric_pressure_hpa")):
                    sched = db.load_schedule("invernadero-orquideas")
                    freq_min = int(sched.get("recording_frequency_minutes") or 60)
                    freq_sec = 15.0 if freq_min <= 1 else float(freq_min * 60)
                    now = time.time()
                    if (now - self._last_field_insert_time) >= freq_sec:
                        db.insert_telemetry(
                            module_id="invernadero-orquideas",
                            temp=st_field["air_temperature"],
                            humidity=st_field["air_humidity"],
                            pressure=st_field["barometric_pressure_hpa"],
                            vpd=st_field["vpd_kpa"],
                            level=st_field["reservoir_level_percent"],
                            pump_active=st_field["pump_active"],
                            servo_angle=0,
                            steps=0,
                            origen="MQTT_WOKWI_ORQUIDEAS",
                        )
                        self._last_field_insert_time = now
                return

            updates: Dict[str, Any] = {}

            if norm_topic == "ASAI/Temperatura":
                updates["air_temperature"] = float(payload_str)
            elif norm_topic == "ASAI/Humedad":
                updates["air_humidity"] = float(payload_str)
            elif norm_topic == "ASAI/Exterior/Temperatura":
                updates["ext_temperature"] = float(payload_str)
            elif norm_topic == "ASAI/Exterior/Humedad":
                updates["ext_humidity"] = float(payload_str)
            elif norm_topic == "ASAI/Nivel":
                updates["reservoir_level_percent"] = float(payload_str)
            elif norm_topic == "ASAI/Presion":
                updates["barometric_pressure_hpa"] = float(payload_str)
            elif norm_topic == "ASAI/DPV":
                updates["vpd_kpa"] = float(payload_str)
            elif norm_topic == "ASAI/Bomba":
                p_up = payload_str.upper()
                if p_up in ("ON", "1", "TRUE"):
                    updates["pump_active"] = True
                elif p_up in ("OFF", "0", "FALSE"):
                    updates["pump_active"] = False
            elif norm_topic == "ASAI/Servo":
                angle = int(float(payload_str))
                updates["vent_servo_angle"] = max(0, min(180, angle))
            elif norm_topic == "ASAI/Alerta":
                self.last_alert = payload_str
                return
            else:
                return

            if updates:
                st = db.save_module_state("celda-01", **updates)

                now = time.time()
                state_changed = False

                if "pump_active" in updates:
                    if self._last_pump_active is not None and self._last_pump_active != updates["pump_active"]:
                        state_changed = True
                    self._last_pump_active = updates["pump_active"]

                if "vent_servo_angle" in updates:
                    if self._last_servo_angle is not None and self._last_servo_angle != updates["vent_servo_angle"]:
                        state_changed = True
                    self._last_servo_angle = updates["vent_servo_angle"]

                time_elapsed = (now - self._last_telemetry_insert_time) >= 15.0

                if state_changed or time_elapsed:
                    db.insert_telemetry(
                        module_id="celda-01",
                        temp=st["air_temperature"],
                        humidity=st["air_humidity"],
                        pressure=st["barometric_pressure_hpa"],
                        vpd=st["vpd_kpa"],
                        level=st["reservoir_level_percent"],
                        pump_active=st["pump_active"],
                        servo_angle=st["vent_servo_angle"],
                        steps=st["stepper_dosing_steps"],
                        origen="MQTT_ESP32",
                    )
                    self._last_telemetry_insert_time = now

        except (ValueError, TypeError) as e:
            logger.warning(f"Payload inválido en tópico MQTT '{topic}' ('{payload}'): {e}")
        except Exception as e:
            logger.error(f"Error procesando mensaje MQTT en '{topic}': {e}")

    def publish_actuator_command(
        self,
        target: str,
        action: str,
        parameter_value: Optional[float] = None,
    ) -> bool:
        """
        Publica un comando manual al ESP32 vía tópicos ASAI/*/cmd.
        Retorna True si el mensaje se despachó al buffer de red del broker, o False en caso de fallo o desconexión.
        """
        if not self._connected or self._client is None:
            return False

        try:
            topic: Optional[str] = None
            payload: Optional[str] = None
            act_upper = action.upper() if action else ""

            if target == "bomba_agua":
                topic = "ASAI/Bomba/cmd"
                payload = "ON" if act_upper == "ON" else "OFF"
            elif target == "servo_ventilacion":
                topic = "ASAI/Servo/cmd"
                angle = max(0, min(180, int(parameter_value or 0)))
                payload = str(angle)
            elif target == "motor_nutrientes":
                topic = "ASAI/Nutrientes/cmd"
                steps = max(0, int(parameter_value or 0))
                payload = str(steps)
            else:
                return False

            res = self._client.publish(topic, payload, qos=0)
            return res.rc == mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS or res.rc == 0
        except Exception as e:
            logger.warning(f"Fallo al publicar comando actuador a MQTT ({target}): {e}")
            return False

    def publish_field_pump(self, turn_on: bool) -> bool:
        """Publica ON/OFF al tópico de aspersión Wokwi de Orquídeas (ASAI/Orquideas/Bomba/cmd)."""
        if not self._connected or self._client is None:
            return False
        try:
            payload = "ON" if turn_on else "OFF"
            res = self._client.publish("ASAI/Orquideas/Bomba/cmd", payload, qos=0)
            return res.rc == mqtt.MQTTErrorCode.MQTT_ERR_SUCCESS or res.rc == 0
        except Exception as e:
            logger.warning(f"Fallo al publicar comando bomba Orquídeas: {e}")
            return False


mqtt_bridge = MqttBridgeService()
