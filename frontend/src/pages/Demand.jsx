import { useCallback } from "react";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import { fetchGeneration, fetchSteel, fetchSummary } from "../api/demand";
import LoadingState from "../components/common/LoadingState";
import AreaStack from "../components/charts/AreaStack";
import PriceLine from "../components/charts/PriceLine";
import MetricCard from "../components/common/MetricCard";
import { formatNumber } from "../utils/formatters";

export default function Demand() {
  const { timeframe } = useTimeframe();

  const generationFn = useCallback(() => fetchGeneration("US", timeframe), [timeframe]);
  const steelFn = useCallback(() => fetchSteel(timeframe), [timeframe]);
  const summaryFn = useCallback(() => fetchSummary(), []);

  const generation = usePolling(generationFn, 120_000, [timeframe]);
  const steel = usePolling(steelFn, 120_000, [timeframe]);
  const summary = usePolling(summaryFn, 120_000);

  const isLoading = generation.loading && !generation.data;

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Demand</h2>

      {/* Generation mix stacked area */}
      <AreaStack
        title="US Generation Mix (GWh)"
        data={generation.data}
        xKey="date"
        areas={[
          { key: "coal", color: "#78716c", label: "Coal" },
          { key: "gas", color: "#06b6d4", label: "Natural Gas" },
          { key: "nuclear", color: "#8b5cf6", label: "Nuclear" },
          { key: "renewables", color: "#22c55e", label: "Renewables" },
        ]}
        height={360}
      />

      {/* Steel production line */}
      <PriceLine
        title="Steel Production Index"
        data={steel.data}
        xKey="date"
        yKey="production"
        height={280}
      />

      {/* Summary cards */}
      {summary.data && (
        <div>
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            Demand Summary
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(Array.isArray(summary.data) ? summary.data : Object.entries(summary.data).map(([k, v]) => ({
              label: k,
              value: v?.value ?? v,
              change_pct: v?.change_pct,
              source: v?.source,
            }))).map((item, i) => (
              <MetricCard
                key={i}
                label={item.label || item.metric || item.name}
                value={formatNumber(item.value)}
                delta={item.change_pct}
                source={item.source}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
