import { useState, useEffect } from "react";
import TimeframeSelector from "../common/TimeframeSelector";
import { fetchHealth } from "../../api/system";

export default function Header() {
  const [lastRefresh, setLastRefresh] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    setLastRefresh(new Date());
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchHealth();
      setLastRefresh(new Date());
    } catch {
      // silent fail - health check may not be available
    } finally {
      setTimeout(() => setRefreshing(false), 600);
    }
  };

  const formatRefreshTime = (date) => {
    if (!date) return "--";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800 flex-shrink-0">
      {/* Title */}
      <div>
        <h1 className="text-lg font-bold text-gray-100 tracking-tight">
          Coal Intelligence
        </h1>
        <p className="text-xs text-gray-500">Equity Research Dashboard</p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4">
        <TimeframeSelector />

        {/* Last refresh */}
        <span className="text-xs text-gray-500 hidden sm:block">
          Updated {formatRefreshTime(lastRefresh)}
        </span>

        {/* Refresh button */}
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-300 bg-gray-800 rounded-md hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <svg
            className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
            />
          </svg>
          Refresh
        </button>
      </div>
    </header>
  );
}
