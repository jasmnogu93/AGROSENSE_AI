package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

/**
 * Payload para POST /schedule (RF1).
 */
public class ScheduleUpdateRequest {

    @SerializedName("active_days")
    private List<String> activeDays;

    @SerializedName("irrigation_time")
    private String irrigationTime;

    @SerializedName("duration_minutes")
    private int durationMinutes;

    public ScheduleUpdateRequest() {
    }

    public ScheduleUpdateRequest(List<String> activeDays, String irrigationTime, int durationMinutes) {
        this.activeDays = activeDays;
        this.irrigationTime = irrigationTime;
        this.durationMinutes = durationMinutes;
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
}
