package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * Datos de telemetría ambiental del módulo de orquídeas.
 */
public class TelemetryData {

    @SerializedName("air_temperature")
    private double airTemperature;

    @SerializedName("air_humidity")
    private double airHumidity;

    @SerializedName("soil_humidity_pct")
    private Double soilHumidityPct;

    @SerializedName("timestamp")
    private String timestamp;

    @SerializedName("status")
    private String status;

    public TelemetryData() {
    }

    public TelemetryData(double airTemperature, double airHumidity, Double soilHumidityPct, String timestamp, String status) {
        this.airTemperature = airTemperature;
        this.airHumidity = airHumidity;
        this.soilHumidityPct = soilHumidityPct;
        this.timestamp = timestamp;
        this.status = status;
    }

    public double getAirTemperature() {
        return airTemperature;
    }

    public void setAirTemperature(double airTemperature) {
        this.airTemperature = airTemperature;
    }

    public double getAirHumidity() {
        return airHumidity;
    }

    public void setAirHumidity(double airHumidity) {
        this.airHumidity = airHumidity;
    }

    public Double getSoilHumidityPct() {
        return soilHumidityPct;
    }

    public void setSoilHumidityPct(Double soilHumidityPct) {
        this.soilHumidityPct = soilHumidityPct;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }
}
