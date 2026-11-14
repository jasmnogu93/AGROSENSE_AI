package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

/**
 * Representa la notificación y próxima cita de riego calculada (RF2).
 */
public class NotificationResponse {

    @SerializedName("scheduled_day")
    private String scheduledDay;

    @SerializedName("scheduled_time")
    private String scheduledTime;

    @SerializedName("is_today")
    private boolean isToday;

    @SerializedName("notification_message")
    private String notificationMessage;

    @SerializedName("active_days")
    private List<String> activeDays;

    public NotificationResponse() {
    }

    public String getScheduledDay() {
        return scheduledDay;
    }

    public void setScheduledDay(String scheduledDay) {
        this.scheduledDay = scheduledDay;
    }

    public String getScheduledTime() {
        return scheduledTime;
    }

    public void setScheduledTime(String scheduledTime) {
        this.scheduledTime = scheduledTime;
    }

    public boolean isToday() {
        return isToday;
    }

    public void setToday(boolean today) {
        isToday = today;
    }

    public String getNotificationMessage() {
        return notificationMessage;
    }

    public void setNotificationMessage(String notificationMessage) {
        this.notificationMessage = notificationMessage;
    }

    public List<String> getActiveDays() {
        return activeDays;
    }

    public void setActiveDays(List<String> activeDays) {
        this.activeDays = activeDays;
    }
}
