package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;
import java.util.Map;

/**
 * Respuesta del endpoint GET /status del servicio AgroField (RF4, RF7).
 */
public class StatusResponse {

    @SerializedName("service")
    private String service;

    @SerializedName("course_target")
    private String courseTarget;

    @SerializedName("profile")
    private OrchidProfile profile;

    @SerializedName("telemetry")
    private TelemetryData telemetry;

    @SerializedName("schedule")
    private ScheduleData schedule;

    @SerializedName("notification")
    private NotificationResponse notification;

    @SerializedName("compliance_status")
    private Map<String, String> complianceStatus;

    @SerializedName("active_alerts")
    private List<String> activeAlerts;

    public StatusResponse() {
    }

    public String getService() {
        return service;
    }

    public void setService(String service) {
        this.service = service;
    }

    public String getCourseTarget() {
        return courseTarget;
    }

    public void setCourseTarget(String courseTarget) {
        this.courseTarget = courseTarget;
    }

    public OrchidProfile getProfile() {
        return profile;
    }

    public void setProfile(OrchidProfile profile) {
        this.profile = profile;
    }

    public TelemetryData getTelemetry() {
        return telemetry;
    }

    public void setTelemetry(TelemetryData telemetry) {
        this.telemetry = telemetry;
    }

    public ScheduleData getSchedule() {
        return schedule;
    }

    public void setSchedule(ScheduleData schedule) {
        this.schedule = schedule;
    }

    public NotificationResponse getNotification() {
        return notification;
    }

    public void setNotification(NotificationResponse notification) {
        this.notification = notification;
    }

    public Map<String, String> getComplianceStatus() {
        return complianceStatus;
    }

    public void setComplianceStatus(Map<String, String> complianceStatus) {
        this.complianceStatus = complianceStatus;
    }

    public List<String> getActiveAlerts() {
        return activeAlerts;
    }

    public void setActiveAlerts(List<String> activeAlerts) {
        this.activeAlerts = activeAlerts;
    }
}
