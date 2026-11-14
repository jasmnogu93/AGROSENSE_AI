package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * Registro de serie temporal en telemetria_historica (RF5, RF6).
 */
public class HistoryRecord {

    @SerializedName("id")
    private int id;

    @SerializedName("modulo_id")
    private String moduloId;

    @SerializedName("fecha_hora")
    private String fechaHora;

    @SerializedName("temp_ambiente")
    private double tempAmbiente;

    @SerializedName("humedad_ambiente")
    private double humedadAmbiente;

    @SerializedName("presion_atmosferica")
    private double presionAtmosferica;

    @SerializedName("dpv_kpa")
    private double dpvKpa;

    @SerializedName("nivel_estanque")
    private double nivelEstanque;

    @SerializedName("bomba_encendida")
    private int bombaEncendida;

    @SerializedName("servo_angulo")
    private int servoAngulo;

    public HistoryRecord() {
    }

    public int getId() {
        return id;
    }

    public void setId(int id) {
        this.id = id;
    }

    public String getModuloId() {
        return moduloId;
    }

    public void setModuloId(String moduloId) {
        this.moduloId = moduloId;
    }

    public String getFechaHora() {
        return fechaHora;
    }

    public void setFechaHora(String fechaHora) {
        this.fechaHora = fechaHora;
    }

    public double getTempAmbiente() {
        return tempAmbiente;
    }

    public void setTempAmbiente(double tempAmbiente) {
        this.tempAmbiente = tempAmbiente;
    }

    public double getHumedadAmbiente() {
        return humedadAmbiente;
    }

    public void setHumedadAmbiente(double humedadAmbiente) {
        this.humedadAmbiente = humedadAmbiente;
    }

    public double getPresionAtmosferica() {
        return presionAtmosferica;
    }

    public void setPresionAtmosferica(double presionAtmosferica) {
        this.presionAtmosferica = presionAtmosferica;
    }

    public double getDpvKpa() {
        return dpvKpa;
    }

    public void setDpvKpa(double dpvKpa) {
        this.dpvKpa = dpvKpa;
    }

    public double getNivelEstanque() {
        return nivelEstanque;
    }

    public void setNivelEstanque(double nivelEstanque) {
        this.nivelEstanque = nivelEstanque;
    }

    public int getBombaEncendida() {
        return bombaEncendida;
    }

    public void setBombaEncendida(int bombaEncendida) {
        this.bombaEncendida = bombaEncendida;
    }

    public int getServoAngulo() {
        return servoAngulo;
    }

    public void setServoAngulo(int servoAngulo) {
        this.servoAngulo = servoAngulo;
    }
}
