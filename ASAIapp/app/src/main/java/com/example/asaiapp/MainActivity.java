package com.example.asaiapp;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.res.ColorStateList;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.IMqttToken;
import org.eclipse.paho.client.mqttv3.MqttAsyncClient;
import org.eclipse.paho.client.mqttv3.MqttCallbackExtended;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;

public class MainActivity extends AppCompatActivity {

    private TextView txtTemperature, txtHumidity, txtExteriorEnv, txtWaterLevel, txtVpd, txtMqttStatus, txtActuatorStatus;
    private ProgressBar progressWaterLevel;
    private Button btnPumpOn, btnPumpOff, btnVentOpen, btnVentClose, btnDoseNutrients;
    private MqttAsyncClient mqttClient;

    private float currentWaterLevel = 100.0f;
    private String currentExtTemp = "--";
    private String currentExtHum = "--";
    private String currentVpd = "--";
    private String currentPressure = "--";
    private String currentPumpState = "OFF";
    private String currentServoAngle = "0°";
    private final Handler reconnectHandler = new Handler(Looper.getMainLooper());
    private boolean isDestroyedFlag = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        txtTemperature = findViewById(R.id.txtTemperature);
        txtHumidity = findViewById(R.id.txtHumidity);
        txtExteriorEnv = findViewById(R.id.txtExteriorEnv);
        txtWaterLevel = findViewById(R.id.txtWaterLevel);
        txtVpd = findViewById(R.id.txtVpd);
        txtMqttStatus = findViewById(R.id.txtMqttStatus);
        txtActuatorStatus = findViewById(R.id.txtActuatorStatus);
        progressWaterLevel = findViewById(R.id.progressWaterLevel);

        btnPumpOn = findViewById(R.id.btnPumpOn);
        btnPumpOff = findViewById(R.id.btnPumpOff);
        btnVentOpen = findViewById(R.id.btnVentOpen);
        btnVentClose = findViewById(R.id.btnVentClose);
        btnDoseNutrients = findViewById(R.id.btnDoseNutrients);

        setupControlButtons();
        connectToMqtt();

        LocalBroadcastManager.getInstance(this).registerReceiver(
                mqttReceiver,
                new IntentFilter("mqtt_data")
        );
    }

    // -- Aqui los botones de Android validan nivel (>= 20%) y PUBLICAN ordenes hacia el ESP32 --
    private void setupControlButtons() {
        btnPumpOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                if (currentWaterLevel < 20.0f) {
                    Toast.makeText(
                            MainActivity.this,
                            "Bloqueado: Nivel de estanque bajo 20% (Anti-Cavitación)",
                            Toast.LENGTH_LONG
                    ).show();
                    return;
                }
                publishCommand("ASAI/Bomba/cmd", "ON", "Orden enviada: Encender Bomba");
                currentPumpState = "ON";
                updateActuatorLabel();
            }
        });

        btnPumpOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                publishCommand("ASAI/Bomba/cmd", "OFF", "Orden enviada: Apagar Bomba");
                currentPumpState = "OFF";
                updateActuatorLabel();
            }
        });

        btnVentOpen.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                publishCommand("ASAI/Servo/cmd", "90", "Ventilación abierta a 90°");
                currentServoAngle = "90°";
                updateActuatorLabel();
            }
        });

        btnVentClose.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                publishCommand("ASAI/Servo/cmd", "0", "Ventilación cerrada a 0°");
                currentServoAngle = "0°";
                updateActuatorLabel();
            }
        });

        btnDoseNutrients.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                publishCommand("ASAI/Nutrientes/cmd", "100", "Dosificando +100 pasos de nutrientes");
            }
        });
    }

    // -- Aqui la app Android PUBLICA un mensaje MQTT al broker en el topico /cmd hacia el ESP32 --
    private void publishCommand(String topic, String payload, String toastMessage) {
        if (mqttClient == null || !mqttClient.isConnected()) {
            Toast.makeText(MainActivity.this, "Reconectando con broker MQTT, intenta en un segundo...", Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            MqttMessage message = new MqttMessage(payload.getBytes());
            message.setQos(0);
            mqttClient.publish(topic, message);
            Toast.makeText(MainActivity.this, toastMessage, Toast.LENGTH_SHORT).show();
        } catch (MqttException e) {
            Log.e("MQTT", "Error al publicar comando: " + e.getMessage());
            Toast.makeText(MainActivity.this, "Error al enviar comando MQTT", Toast.LENGTH_SHORT).show();
        }
    }

    // -- Aqui Android crea el cliente asincrono MQTT, activa reconexion automatica y se conecta a broker.emqx.io --
    private void connectToMqtt() {
        if (isDestroyedFlag) {
            return;
        }
        String mqttServer = "tcp://broker.emqx.io:1883";
        String clientId = MqttClient.generateClientId();
        try {
            if (mqttClient != null) {
                try {
                    mqttClient.close();
                } catch (Exception ignored) {
                }
            }
            mqttClient = new MqttAsyncClient(mqttServer, clientId, null);
            MqttConnectOptions options = new MqttConnectOptions();
            options.setCleanSession(true);
            options.setAutomaticReconnect(true);
            options.setKeepAliveInterval(30);
            options.setConnectionTimeout(15);

            mqttClient.setCallback(new MqttCallbackExtended() {
                @Override
                public void connectComplete(boolean reconnect, String serverURI) {
                    Log.d("MQTT", "Conectado (reconnect=" + reconnect + ") a " + serverURI);
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            txtMqttStatus.setText("MQTT: Conectado a broker.emqx.io");
                            txtMqttStatus.setTextColor(ContextCompat.getColor(MainActivity.this, R.color.Verde));
                        }
                    });
                    // -- Aqui al conectar o reconectar, Android vuelve a llamar subscribeToTopics() --
                    subscribeToTopics();
                }

                @Override
                public void connectionLost(Throwable cause) {
                    String reason = cause != null ? cause.getMessage() : "desconocida";
                    Log.d("MQTT", "Conexión perdida: " + reason + " (auto-reconexión activa)");
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            txtMqttStatus.setText("MQTT: Reconectando...");
                            txtMqttStatus.setTextColor(ContextCompat.getColor(MainActivity.this, R.color.Amarillo));
                        }
                    });
                }

                // -- Aqui Android RECIBE cada dato enviado del ESP32 y lo pasa a la pantalla con LocalBroadcastManager --
                @Override
                public void messageArrived(String topic, MqttMessage message) {
                    String payload = message.toString();
                    Log.d("MQTT", "Mensaje recibido en el tópico: " + topic + ", Mensaje: " + payload);
                    Intent intent = new Intent("mqtt_data");
                    if (topic.equals("ASAI/Temperatura") || topic.equals("ESP8266/Temperatura")) {
                        intent.putExtra("temperature", payload);
                    } else if (topic.equals("ASAI/Humedad") || topic.equals("ESP8266/Humedad")) {
                        intent.putExtra("humidity", payload);
                    } else if (topic.equals("ASAI/Exterior/Temperatura")) {
                        intent.putExtra("ext_temperature", payload);
                    } else if (topic.equals("ASAI/Exterior/Humedad")) {
                        intent.putExtra("ext_humidity", payload);
                    } else if (topic.equals("ASAI/Nivel")) {
                        intent.putExtra("level", payload);
                    } else if (topic.equals("ASAI/DPV")) {
                        intent.putExtra("vpd", payload);
                    } else if (topic.equals("ASAI/Presion")) {
                        intent.putExtra("pressure", payload);
                    } else if (topic.equals("ASAI/Bomba")) {
                        intent.putExtra("pump", payload);
                    } else if (topic.equals("ASAI/Servo")) {
                        intent.putExtra("servo", payload);
                    } else if (topic.equals("ASAI/Alerta")) {
                        intent.putExtra("alert", payload);
                    }
                    LocalBroadcastManager.getInstance(MainActivity.this).sendBroadcast(intent);
                }

                @Override
                public void deliveryComplete(IMqttDeliveryToken token) {
                    // Entrega completada
                }
            });

            mqttClient.connect(options, null, new IMqttActionListener() {
                @Override
                public void onSuccess(IMqttToken asyncActionToken) {
                    Log.d("MQTT", "Conexión exitosa al broker");
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            txtMqttStatus.setText("MQTT: Conectado a broker.emqx.io");
                            txtMqttStatus.setTextColor(ContextCompat.getColor(MainActivity.this, R.color.Verde));
                        }
                    });
                    subscribeToTopics();
                }

                @Override
                public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
                    String errorMsg = exception != null ? exception.getMessage() : "sin detalle";
                    Log.e("MQTT", "Error al conectar: " + errorMsg + " — reintentando en 3s");
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            txtMqttStatus.setText("MQTT: Reintentando conexión...");
                            txtMqttStatus.setTextColor(ContextCompat.getColor(MainActivity.this, R.color.Rojo));
                        }
                    });
                    if (!isDestroyedFlag) {
                        reconnectHandler.postDelayed(new Runnable() {
                            @Override
                            public void run() {
                                connectToMqtt();
                            }
                        }, 3000);
                    }
                }
            });
        } catch (MqttException e) {
            Log.e("MQTT", "Error al crear cliente MQTT: " + e.getMessage());
        }
    }

    // -- Aqui se crean las suscripciones y el cliente Android se SUSCRIBE para escuchar los datos enviados del ESP32 --
    private void subscribeToTopics() {
        String[] topics = new String[]{
                "ASAI/Temperatura",
                "ASAI/Humedad",
                "ASAI/Exterior/Temperatura",
                "ASAI/Exterior/Humedad",
                "ASAI/Nivel",
                "ASAI/DPV",
                "ASAI/Presion",
                "ASAI/Bomba",
                "ASAI/Servo",
                "ASAI/Alerta",
                "ESP8266/Temperatura",
                "ESP8266/Humedad"
        };
        try {
            for (String topic : topics) {
                mqttClient.subscribe(topic, 0);
            }
            Log.d("MQTT", "Suscrito a tópicos de Mini Torre.");
        } catch (MqttException e) {
            Log.e("MQTT", "Error al suscribirse: " + e.getMessage());
        }
    }

    // -- Aqui la pantalla principal de Android recibe el broadcast interno y actualiza las tarjetas en vivo --
    // Receptor de difusión para recibir datos de MQTT
    private final BroadcastReceiver mqttReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String temperature = intent.getStringExtra("temperature");
            String humidity = intent.getStringExtra("humidity");
            String extTemperature = intent.getStringExtra("ext_temperature");
            String extHumidity = intent.getStringExtra("ext_humidity");
            String level = intent.getStringExtra("level");
            String vpd = intent.getStringExtra("vpd");
            String pressure = intent.getStringExtra("pressure");
            String pump = intent.getStringExtra("pump");
            String servo = intent.getStringExtra("servo");
            String alert = intent.getStringExtra("alert");

            if (temperature != null) {
                txtTemperature.setText("Temp. Interior:\n" + temperature + " °C");
            }
            if (humidity != null) {
                txtHumidity.setText("Hum. Interior:\n" + humidity + " %");
            }
            if (extTemperature != null) {
                currentExtTemp = extTemperature;
                txtExteriorEnv.setText("Exterior (DHT11):\n" + currentExtTemp + " °C | " + currentExtHum + " %");
            }
            if (extHumidity != null) {
                currentExtHum = extHumidity;
                txtExteriorEnv.setText("Exterior (DHT11):\n" + currentExtTemp + " °C | " + currentExtHum + " %");
            }
            if (level != null) {
                updateWaterLevelCard(level);
            }
            if (vpd != null) {
                currentVpd = vpd;
                txtVpd.setText("DPV: " + currentVpd + " kPa\nPresión: " + currentPressure + " hPa");
            }
            if (pressure != null) {
                currentPressure = pressure;
                txtVpd.setText("DPV: " + currentVpd + " kPa\nPresión: " + currentPressure + " hPa");
            }
            if (pump != null) {
                currentPumpState = pump;
                updateActuatorLabel();
            }
            if (servo != null) {
                currentServoAngle = servo.endsWith("°") ? servo : servo + "°";
                updateActuatorLabel();
            }
            if ("ESTANQUE_BAJO".equals(alert)) {
                Toast.makeText(
                        MainActivity.this,
                        "Alerta crítica: Estanque bajo (<20%)",
                        Toast.LENGTH_SHORT
                ).show();
            }
        }
    };

    private void updateWaterLevelCard(String levelStr) {
        try {
            float levelVal = Float.parseFloat(levelStr.trim());
            currentWaterLevel = levelVal;
            int clampedProgress = Math.max(0, Math.min(100, Math.round(levelVal)));
            progressWaterLevel.setProgress(clampedProgress);

            int colorRes = levelVal < 20.0f ? R.color.Rojo : R.color.Verde;
            int resolvedColor = ContextCompat.getColor(MainActivity.this, colorRes);
            txtWaterLevel.setTextColor(resolvedColor);
            progressWaterLevel.setProgressTintList(ColorStateList.valueOf(resolvedColor));

            if (levelVal < 20.0f) {
                txtWaterLevel.setText("Nivel Estanque:\n" + levelStr + " % (¡BAJO!)");
            } else {
                txtWaterLevel.setText("Nivel Estanque:\n" + levelStr + " %");
            }
        } catch (NumberFormatException e) {
            txtWaterLevel.setText("Nivel Estanque:\n" + levelStr + " %");
        }
    }

    private void updateActuatorLabel() {
        txtActuatorStatus.setText("Bomba: " + currentPumpState + " | Ventilación: " + currentServoAngle);
    }

    @Override
    protected void onDestroy() {
        isDestroyedFlag = true;
        reconnectHandler.removeCallbacksAndMessages(null);
        super.onDestroy();
        LocalBroadcastManager.getInstance(this).unregisterReceiver(mqttReceiver);
        try {
            if (mqttClient != null) {
                if (mqttClient.isConnected()) {
                    mqttClient.disconnect();
                }
                mqttClient.close();
            }
        } catch (MqttException e) {
            Log.e("MQTT", "Error al desconectar: " + e.getMessage());
        }
    }
}
