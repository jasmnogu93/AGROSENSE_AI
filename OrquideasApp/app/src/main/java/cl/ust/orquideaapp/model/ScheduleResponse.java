package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * Respuesta del endpoint GET /schedule (RF1, RF2).
 */
public class ScheduleResponse {

    @SerializedName("schedule")
    private ScheduleData schedule;

    @SerializedName("notification")
    private NotificationResponse notification;

    public ScheduleResponse() {
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
}
