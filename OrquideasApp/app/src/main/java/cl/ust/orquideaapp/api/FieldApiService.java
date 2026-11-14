package cl.ust.orquideaapp.api;

import cl.ust.orquideaapp.model.HistoryResponse;
import cl.ust.orquideaapp.model.NotificationResponse;
import cl.ust.orquideaapp.model.ScheduleResponse;
import cl.ust.orquideaapp.model.ScheduleUpdateRequest;
import cl.ust.orquideaapp.model.ScheduleUpdateResponse;
import cl.ust.orquideaapp.model.StatusResponse;
import cl.ust.orquideaapp.model.TelemetryRequest;
import cl.ust.orquideaapp.model.TelemetryResponse;
import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.GET;
import retrofit2.http.POST;
import retrofit2.http.Query;

/**
 * Contrato de Endpoints REST de AgroFieldService (/api/v1/services/field/).
 * Implementa el soporte para los requerimientos funcionales RF1 a RF7.
 */
public interface FieldApiService {

    /**
     * Sección 1 (RF4, RF7): Consulta de estado actual del módulo de orquídeas y alertas.
     */
    @GET("status")
    Call<StatusResponse> getStatus();

    /**
     * Sección 2 (RF1): Consulta del calendario de riego semanal y próxima notificación.
     */
    @GET("schedule")
    Call<ScheduleResponse> getSchedule();

    /**
     * Sección 2 (RF1): Actualiza el calendario semanal de riego en SQLite.
     */
    @POST("schedule")
    Call<ScheduleUpdateResponse> updateSchedule(@Body ScheduleUpdateRequest request);

    /**
     * Sección 2 (RF2): Retorna la notificación activa de la hora de riego.
     */
    @GET("notification")
    Call<NotificationResponse> getNotification();

    /**
     * Sección 3 (RF3, RF4, RF6): Ingesta de lectura de sensores Wi-Fi (ESP32).
     */
    @POST("telemetry")
    Call<TelemetryResponse> sendTelemetry(@Body TelemetryRequest request);

    /**
     * Sección 3 (RF5): Consulta el registro histórico de condiciones ambientales.
     */
    @GET("history")
    Call<HistoryResponse> getHistory(@Query("limit") int limit);
}
