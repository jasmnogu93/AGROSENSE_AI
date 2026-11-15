package cl.ust.orquideaapp.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

/**
 * Respuesta del endpoint GET /history (RF5).
 */
public class HistoryResponse {

    @SerializedName("modulo")
    private String modulo;

    @SerializedName("total_records")
    private int totalRecords;

    @SerializedName("history")
    private List<HistoryRecord> history;

    public HistoryResponse() {
    }

    public String getModulo() {
        return modulo;
    }

    public void setModulo(String modulo) {
        this.modulo = modulo;
    }

    public int getTotalRecords() {
        return totalRecords;
    }

    public void setTotalRecords(int totalRecords) {
        this.totalRecords = totalRecords;
    }

    public List<HistoryRecord> getHistory() {
        return history;
    }

    public void setHistory(List<HistoryRecord> history) {
        this.history = history;
    }
}
