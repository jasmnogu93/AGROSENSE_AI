package cl.ust.orquideaapp.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.RecyclerView;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import cl.ust.orquideaapp.R;
import cl.ust.orquideaapp.model.HistoryRecord;

/**
 * Adapter para mostrar los registros históricos de telemetría ambiental (RF5, RF6).
 */
public class HistoryAdapter extends RecyclerView.Adapter<HistoryAdapter.HistoryViewHolder> {

    private final List<HistoryRecord> records = new ArrayList<>();

    public void setRecords(List<HistoryRecord> newRecords) {
        this.records.clear();
        if (newRecords != null) {
            this.records.addAll(newRecords);
        }
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public HistoryViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_history, parent, false);
        return new HistoryViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull HistoryViewHolder holder, int position) {
        HistoryRecord record = records.get(position);
        holder.bind(record);
    }

    @Override
    public int getItemCount() {
        return records.size();
    }

    public static class HistoryViewHolder extends RecyclerView.ViewHolder {

        private final TextView tvItemTimestamp;
        private final TextView tvItemTemp;
        private final TextView tvItemHumidity;
        private final TextView tvItemPressure;
        private final TextView tvItemVpd;
        private final TextView tvItemStatus;

        public HistoryViewHolder(@NonNull View itemView) {
            super(itemView);
            tvItemTimestamp = itemView.findViewById(R.id.tv_item_timestamp);
            tvItemTemp = itemView.findViewById(R.id.tv_item_temp);
            tvItemHumidity = itemView.findViewById(R.id.tv_item_humidity);
            tvItemPressure = itemView.findViewById(R.id.tv_item_pressure);
            tvItemVpd = itemView.findViewById(R.id.tv_item_vpd);
            tvItemStatus = itemView.findViewById(R.id.tv_item_status);
        }

        public void bind(HistoryRecord record) {
            Context context = itemView.getContext();

            tvItemTimestamp.setText(record.getFechaHora() != null ? record.getFechaHora() : "N/A");
            tvItemTemp.setText(String.format(Locale.US, "%.1f °C", record.getTempAmbiente()));
            tvItemHumidity.setText(String.format(Locale.US, "%.1f %% HR", record.getHumedadAmbiente()));
            tvItemPressure.setText(String.format(Locale.US, "%.1f hPa", record.getPresionAtmosferica()));
            tvItemVpd.setText(String.format(Locale.US, "DPV: %.2f kPa", record.getDpvKpa()));

            // Evaluación de rango óptimo para orquídeas: 18-24°C y 75-85% HR
            boolean tempOk = record.getTempAmbiente() >= 18.0 && record.getTempAmbiente() <= 24.0;
            boolean humOk = record.getHumedadAmbiente() >= 75.0 && record.getHumedadAmbiente() <= 85.0;

            if (tempOk && humOk) {
                tvItemStatus.setText("ÓPTIMO");
                tvItemStatus.setTextColor(ContextCompat.getColor(context, R.color.asai_optimal));
            } else {
                tvItemStatus.setText("FUERA RANGO");
                tvItemStatus.setTextColor(ContextCompat.getColor(context, R.color.asai_alert));
            }
        }
    }
}
