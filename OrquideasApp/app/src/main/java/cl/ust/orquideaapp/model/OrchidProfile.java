package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;

/**
 * Parámetros agronómicos de la especie Phalaenopsis sp. (Integración de Competencias II IEI-094).
 */
public class OrchidProfile {

    @SerializedName("especie")
    private String especie;

    @SerializedName("caso_estudio")
    private String casoEstudio;

    @SerializedName("humedad_optima_pct")
    private double humedadOptimaPct;

    @SerializedName("humedad_min_pct")
    private double humedadMinPct;

    @SerializedName("humedad_max_pct")
    private double humedadMaxPct;

    @SerializedName("temp_min_c")
    private double tempMinC;

    @SerializedName("temp_max_c")
    private double tempMaxC;

    @SerializedName("tipo_sustrato")
    private String tipoSustrato;

    @SerializedName("metodo_riego")
    private String metodoRiego;

    public OrchidProfile() {
    }

    public String getEspecie() {
        return especie;
    }

    public void setEspecie(String especie) {
        this.especie = especie;
    }

    public String getCasoEstudio() {
        return casoEstudio;
    }

    public void setCasoEstudio(String casoEstudio) {
        this.casoEstudio = casoEstudio;
    }

    public double getHumedadOptimaPct() {
        return humedadOptimaPct;
    }

    public void setHumedadOptimaPct(double humedadOptimaPct) {
        this.humedadOptimaPct = humedadOptimaPct;
    }

    public double getHumedadMinPct() {
        return humedadMinPct;
    }

    public void setHumedadMinPct(double humedadMinPct) {
        this.humedadMinPct = humedadMinPct;
    }

    public double getHumedadMaxPct() {
        return humedadMaxPct;
    }

    public void setHumedadMaxPct(double humedadMaxPct) {
        this.humedadMaxPct = humedadMaxPct;
    }

    public double getTempMinC() {
        return tempMinC;
    }

    public void setTempMinC(double tempMinC) {
        this.tempMinC = tempMinC;
    }

    public double getTempMaxC() {
        return tempMaxC;
    }

    public void setTempMaxC(double tempMaxC) {
        this.tempMaxC = tempMaxC;
    }

    public String getTipoSustrato() {
        return tipoSustrato;
    }

    public void setTipoSustrato(String tipoSustrato) {
        this.tipoSustrato = tipoSustrato;
    }

    public String getMetodoRiego() {
        return metodoRiego;
    }

    public void setMetodoRiego(String metodoRiego) {
        this.metodoRiego = metodoRiego;
    }
}
