import { useCallback } from "react";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import { fetchBenchmarks, fetchLatestPrices, fetchSpreads, fetchGas } from "../api/pricing";
import LoadingState from "../components/common/LoadingState";
import PriceLine from "../components/charts/PriceLine";
import DataTable from "../components/common/DataTable";
import { formatPrice, formatPct } from "../utils/formatters";

const priceColumns = [
  { key: "name", label: "Benchmark" },
  { key: "price", label: "Price", align: "right", format: (v) => formatPrice(v) },
  { key: "change_pct", label: "Change", align: "right", format: (v) => {
    const p = formatPct(v);
    return <span style={{ color: p.color === "green" ? "#22c55e" : p.color === "red" ? "#ef4444" : "#6b7280" }}>{p.text}</span>;
  }},
  { key: "source", label: "Source" },
];

export default function Pricing() {
  const { timeframe } = useTimeframe();

  const benchmarksFn = useCallback(() => fetchBenchmarks(timeframe), [timeframe]);
  const latestFn = useCallback(() => fetchLatestPrices(), []);
  const spreadsFn = useCallback(() => fetchSpreads(timeframe), [timeframe]);
  const gasFn = useCallback(() => fetchGas(timeframe), [timeframe]);

  const benchmarks = usePolling(benchmarksFn, 120_000, [timeframe]);
  const latest = usePolling(latestFn, 120_000);
  const spreads = usePolling(spreadsFn, 120_000, [timeframe]);
  const gas = usePolling(gasFn, 120_000, [timeframe]);

  const isLoading = benchmarks.loading && !benchmarks.data;

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Coal Benchmark Pricing</h2>

      {/* Coal benchmarks chart */}
      <PriceLine
        title="Coal Benchmarks"
        data={benchmarks.data}
        xKey="date"
        lines={[
          { key: "newcastle", color: "#f59e0b", label: "Newcastle 6000" },
          { key: "api2", color: "#3b82f6", label: "API2 Rotterdam" },
          { key: "api4", color: "#8b5cf6", label: "API4 Richards Bay" },
        ]}
        height={350}
      />

      {/* Gas prices chart */}
      <PriceLine
        title="Natural Gas Prices"
        data={gas.data}
        xKey="date"
        lines={[
          { key: "henry_hub", color: "#06b6d4", label: "Henry Hub" },
          { key: "ttf", color: "#ec4899", label: "TTF (Europe)" },
          { key: "jkm", color: "#f97316", label: "JKM (Asia)" },
        ]}
        height={300}
      />

      {/* Spreads chart */}
      <PriceLine
        title="Gas / Coal Spread"
        data={spreads.data}
        xKey="date"
        lines={[
          { key: "gas_coal_ratio", color: "#10b981", label: "Gas/Coal Ratio" },
        ]}
        height={250}
      />

      {/* Latest prices table */}
      <div className="card">
        <div className="card-header">Latest Prices</div>
        <DataTable columns={priceColumns} data={latest.data} />
      </div>
    </div>
  );
}
