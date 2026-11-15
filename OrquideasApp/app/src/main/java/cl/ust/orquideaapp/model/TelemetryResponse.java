package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * Respuesta de POST /telemetry (RF3, RF4, RF6).
 */
public class TelemetryResponse {

    @SerializedName("status")
    private String status;

    @SerializedName("message")
    private String message;

    @SerializedName("telemetry")
    private TelemetryData telemetry;

    public TelemetryResponse() {
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

    public TelemetryData getTelemetry() {
        return telemetry;
    }

    public void setTelemetry(TelemetryData telemetry) {
        this.telemetry = telemetry;
    }
}
