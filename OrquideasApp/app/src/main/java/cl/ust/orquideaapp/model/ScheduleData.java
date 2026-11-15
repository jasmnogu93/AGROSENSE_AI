package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

/**
 * Representa el calendario de riego semanal almacenado en la base de datos (RF1).
 */
public class ScheduleData {

    @SerializedName("modulo_id")
    private String moduloId;

    @SerializedName("active_days")
    private List<String> activeDays;

    @SerializedName("irrigation_time")
    private String irrigationTime;

    @SerializedName("duration_minutes")
    private int durationMinutes;

    @SerializedName("modo")
    private String modo;

    public ScheduleData() {
    }

    public String getModuloId() {
        return moduloId;
    }

    public void setModuloId(String moduloId) {
        this.moduloId = moduloId;
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

    public String getModo() {
        return modo;
    }

    public void setModo(String modo) {
        this.modo = modo;
    }
}
