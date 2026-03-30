import { useCallback } from "react";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import { fetchIndicators, fetchLatest } from "../api/macro";
import LoadingState from "../components/common/LoadingState";
import PriceLine from "../components/charts/PriceLine";
import DataTable from "../components/common/DataTable";
import { formatPct } from "../utils/formatters";

const macroColumns = [
  { key: "name", label: "Indicator" },
  { key: "value", label: "Value", align: "right", format: (v) => (v != null ? Number(v).toFixed(2) : "--") },
  { key: "change_pct", label: "Change", align: "right", format: (v) => {
    const p = formatPct(v);
    return <span style={{ color: p.color === "green" ? "#22c55e" : p.color === "red" ? "#ef4444" : "#6b7280" }}>{p.text}</span>;
  }},
  { key: "source", label: "Source" },
];

export default function Macro() {
  const { timeframe } = useTimeframe();

  const indicatorsFn = useCallback(
    () => fetchIndicators(["AUD_USD", "DXY", "US10Y"], timeframe),
    [timeframe],
  );
  const latestFn = useCallback(() => fetchLatest(), []);

  const indicators = usePolling(indicatorsFn, 120_000, [timeframe]);
  const latest = usePolling(latestFn, 120_000);

  const isLoading = indicators.loading && !indicators.data;

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Macro Indicators</h2>

      {/* AUD/USD */}
      <PriceLine
        title="AUD/USD Exchange Rate"
        data={indicators.data?.AUD_USD || indicators.data}
        xKey="date"
        yKey="value"
        height={280}
      />

      {/* DXY */}
      <PriceLine
        title="US Dollar Index (DXY)"
        data={indicators.data?.DXY}
        xKey="date"
        yKey="value"
        height={280}
      />

      {/* 10Y Yield */}
      <PriceLine
        title="US 10-Year Treasury Yield"
        data={indicators.data?.US10Y}
        xKey="date"
        yKey="value"
        height={280}
      />

      {/* Latest values table */}
      <div className="card">
        <div className="card-header">Latest Macro Values</div>
        <DataTable columns={macroColumns} data={latest.data} />
      </div>
    </div>
  );
}
