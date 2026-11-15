package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * Payload para POST /telemetry (RF3, RF4).
 */
public class TelemetryRequest {

    @SerializedName("air_temperature")
    private double airTemperature;

    @SerializedName("air_humidity")
    private double airHumidity;

    @SerializedName("soil_humidity_pct")
    private Double soilHumidityPct;

    public TelemetryRequest() {
    }

    public TelemetryRequest(double airTemperature, double airHumidity, Double soilHumidityPct) {
        this.airTemperature = airTemperature;
        this.airHumidity = airHumidity;
        this.soilHumidityPct = soilHumidityPct;
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
}
