import { useCallback, useState } from "react";
import usePolling from "../hooks/usePolling";
import { fetchHealth, fetchFreshness, triggerRefresh } from "../api/system";
import LoadingState from "../components/common/LoadingState";
import MetricCard from "../components/common/MetricCard";
import DataTable from "../components/common/DataTable";
import { formatTimestamp } from "../utils/formatters";

const freshnessColumns = [
  { key: "source", label: "Data Source" },
  { key: "last_updated", label: "Last Updated", format: (v) => formatTimestamp(v) },
  {
    key: "status",
    label: "Status",
    format: (v) => {
      const colors = {
        fresh: "text-green-400 bg-green-900/30",
        stale: "text-amber-400 bg-amber-900/30",
        error: "text-red-400 bg-red-900/30",
      };
      const c = colors[v] || colors.stale;
      return (
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${c}`}>
          {v || "unknown"}
        </span>
      );
    },
  },
  { key: "records", label: "Records", align: "right" },
];

const REFRESH_DOMAINS = [
  { key: "pricing", label: "Pricing" },
  { key: "supply", label: "Supply" },
  { key: "demand", label: "Demand" },
  { key: "company", label: "Company" },
  { key: "macro", label: "Macro" },
  { key: "weather", label: "Weather" },
  { key: "sentiment", label: "Sentiment" },
];

export default function Settings() {
  const [refreshingDomain, setRefreshingDomain] = useState(null);

  const healthFn = useCallback(() => fetchHealth(), []);
  const freshnessFn = useCallback(() => fetchFreshness(), []);

  const health = usePolling(healthFn, 30_000);
  const freshness = usePolling(freshnessFn, 60_000);

  const isLoading = health.loading && !health.data;

  const handleRefresh = async (domain) => {
    setRefreshingDomain(domain);
    try {
      await triggerRefresh(domain);
      freshness.refresh();
    } catch (err) {
      console.error(`Failed to refresh ${domain}:`, err);
    } finally {
      setTimeout(() => setRefreshingDomain(null), 1000);
    }
  };

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Settings</h2>

      {/* System health */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
          System Health
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricCard
            label="API Status"
            value={health.data?.status || "Unknown"}
            source="System"
          />
          <MetricCard
            label="Database"
            value={health.data?.database || "Unknown"}
            source="System"
          />
          <MetricCard
            label="Uptime"
            value={health.data?.uptime || "--"}
            source="System"
          />
          <MetricCard
            label="Version"
            value={health.data?.version || "1.0.0"}
            source="System"
          />
        </div>
      </div>

      {/* Data freshness table */}
      <div className="card">
        <div className="card-header">Data Freshness</div>
        <DataTable columns={freshnessColumns} data={freshness.data} />
      </div>

      {/* Manual refresh buttons */}
      <div className="card">
        <div className="card-header">Manual Refresh</div>
        <p className="text-xs text-gray-500 mb-4">
          Trigger a manual data refresh for each domain. This will pull the latest data from all sources.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {REFRESH_DOMAINS.map((d) => (
            <button
              key={d.key}
              onClick={() => handleRefresh(d.key)}
              disabled={refreshingDomain === d.key}
              className="flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-300 bg-gray-800 border border-gray-700 rounded-md hover:bg-gray-700 hover:border-gray-600 transition-colors disabled:opacity-50"
            >
              {refreshingDomain === d.key ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                </svg>
              )}
              {d.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
