package cl.ust.orquideaapp;

import android.app.TimePickerDialog;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;

import com.google.android.material.button.MaterialButton;
import com.google.android.material.card.MaterialCardView;
import com.google.android.material.chip.Chip;
import com.google.android.material.textfield.TextInputEditText;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import cl.ust.orquideaapp.adapter.HistoryAdapter;
import cl.ust.orquideaapp.api.ApiClient;
import cl.ust.orquideaapp.api.FieldApiService;
import cl.ust.orquideaapp.model.HistoryRecord;
import cl.ust.orquideaapp.model.HistoryResponse;
import cl.ust.orquideaapp.model.NotificationResponse;
import cl.ust.orquideaapp.model.ScheduleData;
import cl.ust.orquideaapp.model.ScheduleResponse;
import cl.ust.orquideaapp.model.ScheduleUpdateRequest;
import cl.ust.orquideaapp.model.ScheduleUpdateResponse;
import cl.ust.orquideaapp.model.StatusResponse;
import cl.ust.orquideaapp.model.TelemetryData;
import cl.ust.orquideaapp.model.TelemetryRequest;
import cl.ust.orquideaapp.model.TelemetryResponse;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

/**
 * Actividad Principal de AgroSense AI - Invernadero de Orquídeas.
 * Implementa el control y monitoreo de AgroFieldService (RF1 a RF7).
 */
public class MainActivity extends AppCompatActivity {

    private FieldApiService apiService;

    // UI - General
    private SwipeRefreshLayout swipeRefresh;

    // UI - Sección 1: Estado y Alertas (RF4, RF7)
    private MaterialCardView cardTemp;
    private MaterialCardView cardHum;
    private TextView tvTemperature;
    private TextView tvTempStatus;
    private TextView tvHumidity;
    private TextView tvHumStatus;
    private TextView tvSoilHumidity;
    private TextView tvModuleStatus;
    private TextView tvLastUpdated;
    private LinearLayout llAlertsContainer;
    private TextView tvNoAlerts;
    private MaterialButton btnRefreshStatus;

    // UI - Sección 2: Riego Semanal y Notificación (RF1, RF2)
    private MaterialCardView cardNotificationBanner;
    private TextView tvNotificationMessage;
    private TextView tvNotificationBadge;
    private Chip chipLun;
    private Chip chipMar;
    private Chip chipMie;
    private Chip chipJue;
    private Chip chipVie;
    private Chip chipSab;
    private Chip chipDom;
    private TextInputEditText etIrrigationTime;
    private TextInputEditText etDurationMinutes;
    private MaterialButton btnSaveSchedule;

    // UI - Sección 3: Telemetría e Historial (RF3, RF5, RF6)
    private TextInputEditText etTelemetryTemp;
    private TextInputEditText etTelemetryHum;
    private TextInputEditText etTelemetrySoil;
    private MaterialButton btnSendTelemetry;
    private RecyclerView rvHistory;
    private TextView tvEmptyHistory;
    private HistoryAdapter historyAdapter;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WindowCompat.enableEdgeToEdge(getWindow());
        setContentView(R.layout.activity_main);

        View mainView = findViewById(R.id.main);
        if (mainView != null) {
            ViewCompat.setOnApplyWindowInsetsListener(mainView, (v, insets) -> {
                Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
                v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
                return insets;
            });
        }

        apiService = ApiClient.getFieldApiService();

        bindViews();
        setupListeners();
        setupRecyclerView();

        loadAllData();
    }

    private void bindViews() {
        swipeRefresh = findViewById(R.id.swipe_refresh);

        // Sección 1
        cardTemp = findViewById(R.id.card_temp);
        cardHum = findViewById(R.id.card_hum);
        tvTemperature = findViewById(R.id.tv_temperature);
        tvTempStatus = findViewById(R.id.tv_temp_status);
        tvHumidity = findViewById(R.id.tv_humidity);
        tvHumStatus = findViewById(R.id.tv_hum_status);
        tvSoilHumidity = findViewById(R.id.tv_soil_humidity);
        tvModuleStatus = findViewById(R.id.tv_module_status);
        tvLastUpdated = findViewById(R.id.tv_last_updated);
        llAlertsContainer = findViewById(R.id.ll_alerts_container);
        tvNoAlerts = findViewById(R.id.tv_no_alerts);
        btnRefreshStatus = findViewById(R.id.btn_refresh_status);

        // Sección 2
        cardNotificationBanner = findViewById(R.id.card_notification_banner);
        tvNotificationMessage = findViewById(R.id.tv_notification_message);
        tvNotificationBadge = findViewById(R.id.tv_notification_badge);
        chipLun = findViewById(R.id.chip_lun);
        chipMar = findViewById(R.id.chip_mar);
        chipMie = findViewById(R.id.chip_mie);
        chipJue = findViewById(R.id.chip_jue);
        chipVie = findViewById(R.id.chip_vie);
        chipSab = findViewById(R.id.chip_sab);
        chipDom = findViewById(R.id.chip_dom);
        etIrrigationTime = findViewById(R.id.et_irrigation_time);
        etDurationMinutes = findViewById(R.id.et_duration_minutes);
        btnSaveSchedule = findViewById(R.id.btn_save_schedule);

        // Sección 3
        etTelemetryTemp = findViewById(R.id.et_telemetry_temp);
        etTelemetryHum = findViewById(R.id.et_telemetry_hum);
        etTelemetrySoil = findViewById(R.id.et_telemetry_soil);
        btnSendTelemetry = findViewById(R.id.btn_send_telemetry);
        rvHistory = findViewById(R.id.rv_history);
        tvEmptyHistory = findViewById(R.id.tv_empty_history);
    }

    private void setupListeners() {
        swipeRefresh.setOnRefreshListener(this::loadAllData);

        btnRefreshStatus.setOnClickListener(v -> loadAllData());

        etIrrigationTime.setOnClickListener(v -> showTimePickerDialog());

        btnSaveSchedule.setOnClickListener(v -> saveSchedule());

        btnSendTelemetry.setOnClickListener(v -> sendTelemetry());
    }

    private void setupRecyclerView() {
        historyAdapter = new HistoryAdapter();
        rvHistory.setLayoutManager(new LinearLayoutManager(this));
        rvHistory.setAdapter(historyAdapter);
    }

    private void loadAllData() {
        swipeRefresh.setRefreshing(true);
        fetchStatus();
        fetchScheduleAndNotification();
        fetchHistory();
    }

    // =========================================================================
    // SECCIÓN 1: ESTADO Y ALERTAS (RF4, RF7)
    // =========================================================================

    private void fetchStatus() {
        apiService.getStatus().enqueue(new Callback<StatusResponse>() {
            @Override
            public void onResponse(@NonNull Call<StatusResponse> call, @NonNull Response<StatusResponse> response) {
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    StatusResponse status = response.body();
                    updateStatusUI(status);
                } else {
                    showError("Error al consultar estado (HTTP " + response.code() + ")");
                }
            }

            @Override
            public void onFailure(@NonNull Call<StatusResponse> call, @NonNull Throwable t) {
                swipeRefresh.setRefreshing(false);
                showError("Fallo de conexión al consultar estado: " + t.getMessage());
            }
        });
    }

    private void updateStatusUI(StatusResponse status) {
        TelemetryData telemetry = status.getTelemetry();
        if (telemetry != null) {
            double temp = telemetry.getAirTemperature();
            double hum = telemetry.getAirHumidity();

            tvTemperature.setText(String.format(Locale.US, "%.1f °C", temp));
            tvHumidity.setText(String.format(Locale.US, "%.1f %%", hum));

            // Rango óptimo de temperatura para orquídeas: 18 - 24 °C (RF4)
            if (temp >= 18.0 && temp <= 24.0) {
                tvTempStatus.setText("Óptimo (18–24 °C)");
                tvTempStatus.setTextColor(ContextCompat.getColor(this, R.color.asai_optimal));
                tvTempStatus.setBackgroundResource(R.drawable.bg_badge_optimal);
            } else {
                tvTempStatus.setText("ALERTA TÉRMICA");
                tvTempStatus.setTextColor(ContextCompat.getColor(this, R.color.asai_alert));
                tvTempStatus.setBackgroundResource(R.drawable.bg_badge_alert);
            }

            // Rango óptimo de humedad: Objetivo 80% (75 - 85%) (RF4)
            if (hum >= 75.0 && hum <= 85.0) {
                tvHumStatus.setText("Óptimo (Obj. 80%)");
                tvHumStatus.setTextColor(ContextCompat.getColor(this, R.color.asai_optimal));
                tvHumStatus.setBackgroundResource(R.drawable.bg_badge_optimal);
            } else if (hum < 75.0) {
                tvHumStatus.setText("ALERTA HUMEDAD BAJA");
                tvHumStatus.setTextColor(ContextCompat.getColor(this, R.color.asai_alert));
                tvHumStatus.setBackgroundResource(R.drawable.bg_badge_alert);
            } else {
                tvHumStatus.setText("AVISO SOBREHUMEDAD");
                tvHumStatus.setTextColor(ContextCompat.getColor(this, R.color.asai_warning));
                tvHumStatus.setBackgroundResource(R.drawable.bg_badge_warning);
            }

            if (telemetry.getSoilHumidityPct() != null) {
                tvSoilHumidity.setText(String.format(Locale.US, "Sustrato: %.1f %%", telemetry.getSoilHumidityPct()));
            } else {
                tvSoilHumidity.setText("Sustrato: N/D");
            }

            tvModuleStatus.setText("Módulo: " + (telemetry.getStatus() != null ? telemetry.getStatus() : "ACTIVO"));
            tvLastUpdated.setText("Última actualización: " + (telemetry.getTimestamp() != null ? telemetry.getTimestamp() : "En vivo"));
        }

        // Renderizado dinámico de alertas activas (RF4, RF7)
        renderActiveAlerts(status.getActiveAlerts());

        // Actualizar banner si notification viene presente en status
        if (status.getNotification() != null) {
            updateNotificationBanner(status.getNotification());
        }
    }

    private void renderActiveAlerts(List<String> alerts) {
        llAlertsContainer.removeAllViews();

        if (alerts == null || alerts.isEmpty()) {
            tvNoAlerts.setVisibility(View.VISIBLE);
            llAlertsContainer.addView(tvNoAlerts);
        } else {
            tvNoAlerts.setVisibility(View.GONE);
            for (String alertText : alerts) {
                MaterialCardView cardAlert = new MaterialCardView(this);
                cardAlert.setRadius(getResources().getDimension(R.dimen.cardview_default_radius));
                cardAlert.setStrokeWidth(2);

                boolean isWarning = alertText.startsWith("AVISO");
                int strokeColor = ContextCompat.getColor(this, isWarning ? R.color.asai_warning : R.color.asai_alert);
                int bgColor = ContextCompat.getColor(this, isWarning ? R.color.asai_warning_bg : R.color.asai_alert_bg);

                cardAlert.setStrokeColor(strokeColor);
                cardAlert.setCardBackgroundColor(bgColor);

                LinearLayout layout = new LinearLayout(this);
                layout.setOrientation(LinearLayout.HORIZONTAL);
                layout.setPadding(24, 20, 24, 20);
                layout.setGravity(Gravity.CENTER_VERTICAL);

                ImageView icon = new ImageView(this);
                icon.setImageResource(R.drawable.ic_warning);
                icon.setColorFilter(strokeColor);
                LinearLayout.LayoutParams iconParams = new LinearLayout.LayoutParams(48, 48);
                iconParams.setMarginEnd(16);
                layout.addView(icon, iconParams);

                TextView tvAlert = new TextView(this);
                tvAlert.setText(alertText);
                tvAlert.setTextColor(strokeColor);
                tvAlert.setTextSize(12);
                tvAlert.setLayoutParams(new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                ));
                layout.addView(tvAlert);

                cardAlert.addView(layout);

                LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                        LinearLayout.LayoutParams.MATCH_PARENT,
                        LinearLayout.LayoutParams.WRAP_CONTENT
                );
                cardParams.setMargins(0, 8, 0, 8);
                llAlertsContainer.addView(cardAlert, cardParams);
            }
        }
    }

    // =========================================================================
    // SECCIÓN 2: RIEGO SEMANAL Y NOTIFICACIÓN (RF1, RF2)
    // =========================================================================

    private void fetchScheduleAndNotification() {
        apiService.getSchedule().enqueue(new Callback<ScheduleResponse>() {
            @Override
            public void onResponse(@NonNull Call<ScheduleResponse> call, @NonNull Response<ScheduleResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    ScheduleResponse data = response.body();
                    updateScheduleUI(data.getSchedule());
                    updateNotificationBanner(data.getNotification());
                }
            }

            @Override
            public void onFailure(@NonNull Call<ScheduleResponse> call, @NonNull Throwable t) {
                // Notificar en caso de error crítico
            }
        });
    }

    private void updateScheduleUI(ScheduleData schedule) {
        if (schedule == null) return;

        List<String> activeDays = schedule.getActiveDays() != null ? schedule.getActiveDays() : new ArrayList<>();
        chipLun.setChecked(activeDays.contains("Lun"));
        chipMar.setChecked(activeDays.contains("Mar"));
        chipMie.setChecked(activeDays.contains("Mié"));
        chipJue.setChecked(activeDays.contains("Jue"));
        chipVie.setChecked(activeDays.contains("Vie"));
        chipSab.setChecked(activeDays.contains("Sáb"));
        chipDom.setChecked(activeDays.contains("Dom"));

        if (schedule.getIrrigationTime() != null) {
            etIrrigationTime.setText(schedule.getIrrigationTime());
        }
        etDurationMinutes.setText(String.valueOf(schedule.getDurationMinutes()));
    }

    private void updateNotificationBanner(NotificationResponse notification) {
        if (notification == null) return;

        tvNotificationMessage.setText(notification.getNotificationMessage());
        if (notification.isToday()) {
            tvNotificationBadge.setText("¡RIEGO HOY!");
            tvNotificationBadge.setTextColor(ContextCompat.getColor(this, R.color.asai_optimal));
            tvNotificationBadge.setBackgroundResource(R.drawable.bg_badge_optimal);
        } else {
            tvNotificationBadge.setText("PRÓXIMO: " + (notification.getScheduledDay() != null ? notification.getScheduledDay() : "PROGRAMADO"));
            tvNotificationBadge.setTextColor(ContextCompat.getColor(this, R.color.asai_banner_text));
            tvNotificationBadge.setBackgroundResource(R.drawable.bg_badge_optimal);
        }
    }

    private void showTimePickerDialog() {
        String current = etIrrigationTime.getText() != null ? etIrrigationTime.getText().toString() : "08:30";
        int hour = 8;
        int minute = 30;

        if (current.contains(":")) {
            String[] parts = current.split(":");
            try {
                hour = Integer.parseInt(parts[0].trim());
                minute = Integer.parseInt(parts[1].trim());
            } catch (NumberFormatException ignored) {
            }
        }

        TimePickerDialog dialog = new TimePickerDialog(this, (view, hourOfDay, minuteOfHour) -> {
            String formattedTime = String.format(Locale.US, "%02d:%02d", hourOfDay, minuteOfHour);
            etIrrigationTime.setText(formattedTime);
        }, hour, minute, true);

        dialog.show();
    }

    private void saveSchedule() {
        List<String> activeDays = new ArrayList<>();
        if (chipLun.isChecked()) activeDays.add("Lun");
        if (chipMar.isChecked()) activeDays.add("Mar");
        if (chipMie.isChecked()) activeDays.add("Mié");
        if (chipJue.isChecked()) activeDays.add("Jue");
        if (chipVie.isChecked()) activeDays.add("Vie");
        if (chipSab.isChecked()) activeDays.add("Sáb");
        if (chipDom.isChecked()) activeDays.add("Dom");

        if (activeDays.isEmpty()) {
            Toast.makeText(this, "Debe seleccionar al menos un día de la semana.", Toast.LENGTH_SHORT).show();
            return;
        }

        String timeStr = etIrrigationTime.getText() != null ? etIrrigationTime.getText().toString().trim() : "";
        if (!timeStr.matches("^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")) {
            Toast.makeText(this, "Formato de hora no válido. Use HH:mm (ej. 08:30).", Toast.LENGTH_SHORT).show();
            return;
        }

        String durationStr = etDurationMinutes.getText() != null ? etDurationMinutes.getText().toString().trim() : "";
        int duration;
        try {
            duration = Integer.parseInt(durationStr);
            if (duration < 1 || duration > 120) {
                Toast.makeText(this, "La duración del riego debe estar entre 1 y 120 minutos.", Toast.LENGTH_SHORT).show();
                return;
            }
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Ingrese un número válido para la duración.", Toast.LENGTH_SHORT).show();
            return;
        }

        btnSaveSchedule.setEnabled(false);
        ScheduleUpdateRequest request = new ScheduleUpdateRequest(activeDays, timeStr, duration);

        apiService.updateSchedule(request).enqueue(new Callback<ScheduleUpdateResponse>() {
            @Override
            public void onResponse(@NonNull Call<ScheduleUpdateResponse> call, @NonNull Response<ScheduleUpdateResponse> response) {
                btnSaveSchedule.setEnabled(true);
                if (response.isSuccessful() && response.body() != null) {
                    ScheduleUpdateResponse updateResp = response.body();
                    Toast.makeText(MainActivity.this, updateResp.getMessage(), Toast.LENGTH_LONG).show();
                    if (updateResp.getNotification() != null) {
                        tvNotificationMessage.setText(updateResp.getNotification());
                    }
                    // Refrescar estado y notificación activa
                    fetchScheduleAndNotification();
                } else {
                    showError("Error al guardar calendario (HTTP " + response.code() + ")");
                }
            }

            @Override
            public void onFailure(@NonNull Call<ScheduleUpdateResponse> call, @NonNull Throwable t) {
                btnSaveSchedule.setEnabled(true);
                showError("Fallo de red al guardar calendario: " + t.getMessage());
            }
        });
    }

    // =========================================================================
    // SECCIÓN 3: TELEMETRÍA E HISTORIAL (RF3, RF5, RF6)
    // =========================================================================

    private void sendTelemetry() {
        String tempStr = etTelemetryTemp.getText() != null ? etTelemetryTemp.getText().toString().trim() : "";
        String humStr = etTelemetryHum.getText() != null ? etTelemetryHum.getText().toString().trim() : "";
        String soilStr = etTelemetrySoil.getText() != null ? etTelemetrySoil.getText().toString().trim() : "";

        if (TextUtils.isEmpty(tempStr) || TextUtils.isEmpty(humStr)) {
            Toast.makeText(this, "Temperatura y Humedad son requeridas.", Toast.LENGTH_SHORT).show();
            return;
        }

        double temp;
        double hum;
        Double soil = null;

        try {
            temp = Double.parseDouble(tempStr.replace(",", "."));
            if (temp < -10.0 || temp > 60.0) {
                Toast.makeText(this, "Temperatura fuera de rango agronómico (-10 a 60 °C).", Toast.LENGTH_SHORT).show();
                return;
            }
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Temperatura no válida.", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            hum = Double.parseDouble(humStr.replace(",", "."));
            if (hum < 0.0 || hum > 100.0) {
                Toast.makeText(this, "Humedad debe estar entre 0% y 100%.", Toast.LENGTH_SHORT).show();
                return;
            }
        } catch (NumberFormatException e) {
            Toast.makeText(this, "Humedad no válida.", Toast.LENGTH_SHORT).show();
            return;
        }

        if (!TextUtils.isEmpty(soilStr)) {
            try {
                soil = Double.parseDouble(soilStr.replace(",", "."));
                if (soil < 0.0 || soil > 100.0) {
                    Toast.makeText(this, "Humedad de sustrato debe estar entre 0% y 100%.", Toast.LENGTH_SHORT).show();
                    return;
                }
            } catch (NumberFormatException e) {
                Toast.makeText(this, "Humedad de sustrato no válida.", Toast.LENGTH_SHORT).show();
                return;
            }
        }

        btnSendTelemetry.setEnabled(false);
        TelemetryRequest request = new TelemetryRequest(temp, hum, soil);

        apiService.sendTelemetry(request).enqueue(new Callback<TelemetryResponse>() {
            @Override
            public void onResponse(@NonNull Call<TelemetryResponse> call, @NonNull Response<TelemetryResponse> response) {
                btnSendTelemetry.setEnabled(true);
                if (response.isSuccessful() && response.body() != null) {
                    Toast.makeText(MainActivity.this, "✅ Telemetría registrada en SQLite con éxito (RF5, RF6)", Toast.LENGTH_SHORT).show();
                    // Refrescar Sección 1 (Tiempo Real) y Sección 3 (Historial)
                    fetchStatus();
                    fetchHistory();
                } else {
                    showError("Error al enviar telemetría (HTTP " + response.code() + ")");
                }
            }

            @Override
            public void onFailure(@NonNull Call<TelemetryResponse> call, @NonNull Throwable t) {
                btnSendTelemetry.setEnabled(true);
                showError("Fallo de red al transmitir telemetría: " + t.getMessage());
            }
        });
    }

    private void fetchHistory() {
        apiService.getHistory(10).enqueue(new Callback<HistoryResponse>() {
            @Override
            public void onResponse(@NonNull Call<HistoryResponse> call, @NonNull Response<HistoryResponse> response) {
                if (response.isSuccessful() && response.body() != null) {
                    List<HistoryRecord> records = response.body().getHistory();
                    if (records != null && !records.isEmpty()) {
                        historyAdapter.setRecords(records);
                        rvHistory.setVisibility(View.VISIBLE);
                        tvEmptyHistory.setVisibility(View.GONE);
                    } else {
                        rvHistory.setVisibility(View.GONE);
                        tvEmptyHistory.setVisibility(View.VISIBLE);
                    }
                }
            }

            @Override
            public void onFailure(@NonNull Call<HistoryResponse> call, @NonNull Throwable t) {
                // Error de red no bloqueante
            }
        });
    }

    private void showError(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
    }
}
