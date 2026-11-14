package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

/**
 * Respuesta del endpoint POST /schedule (RF1).
 */
public class ScheduleUpdateResponse {

    @SerializedName("status")
    private String status;

    @SerializedName("message")
    private String message;

    @SerializedName("active_days")
    private List<String> activeDays;

    @SerializedName("irrigation_time")
    private String irrigationTime;

    @SerializedName("duration_minutes")
    private int durationMinutes;

    @SerializedName("notification")
    private String notification;

    public ScheduleUpdateResponse() {
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public List<String> getActiveDays() {
        return activeDays;
    }

    public void setActiveDays(List<String> activeDays) {
        this.activeDays = activeDays;
    }

    public String getIrrigationTime() {
        return irrigationTime;
    }

    public void setIrrigationTime(String irrigationTime) {
        this.irrigationTime = irrigationTime;
    }

    public int getDurationMinutes() {
        return durationMinutes;
    }

    public void setDurationMinutes(int durationMinutes) {
        this.durationMinutes = durationMinutes;
    }

    public String getNotification() {
        return notification;
    }

    public void setNotification(String notification) {
        this.notification = notification;
    }
}
