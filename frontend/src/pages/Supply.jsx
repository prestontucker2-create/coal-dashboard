import { useCallback } from "react";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import { fetchProduction, fetchInventories, fetchSummary } from "../api/supply";
import LoadingState from "../components/common/LoadingState";
import PriceLine from "../components/charts/PriceLine";
import DataTable from "../components/common/DataTable";
import { formatNumber, formatPct } from "../utils/formatters";

const summaryColumns = [
  { key: "metric", label: "Metric" },
  { key: "value", label: "Value", align: "right", format: (v) => formatNumber(v) },
  { key: "change_pct", label: "Change", align: "right", format: (v) => {
    const p = formatPct(v);
    return <span style={{ color: p.color === "green" ? "#22c55e" : p.color === "red" ? "#ef4444" : "#6b7280" }}>{p.text}</span>;
  }},
  { key: "unit", label: "Unit" },
  { key: "source", label: "Source" },
];

export default function Supply() {
  const { timeframe } = useTimeframe();

  const productionFn = useCallback(() => fetchProduction("US", timeframe), [timeframe]);
  const inventoriesFn = useCallback(() => fetchInventories(timeframe), [timeframe]);
  const summaryFn = useCallback(() => fetchSummary(), []);

  const production = usePolling(productionFn, 120_000, [timeframe]);
  const inventories = usePolling(inventoriesFn, 120_000, [timeframe]);
  const summary = usePolling(summaryFn, 120_000);

  const isLoading = production.loading && !production.data;

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Supply</h2>

      {/* US Coal production */}
      <PriceLine
        title="US Coal Production"
        data={production.data}
        xKey="date"
        yKey="production"
        height={320}
      />

      {/* Inventories */}
      <PriceLine
        title="US Coal Inventories"
        data={inventories.data}
        xKey="date"
        yKey="inventory"
        height={300}
      />

      {/* Summary table */}
      <div className="card">
        <div className="card-header">Supply Summary</div>
        <DataTable columns={summaryColumns} data={summary.data} />
      </div>
    </div>
  );
}
