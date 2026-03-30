import { useCallback } from "react";
import usePolling from "../hooks/usePolling";
import { fetchOverview } from "../api/overview";
import LoadingState from "../components/common/LoadingState";
import KeyPricesStrip from "../components/widgets/KeyPricesStrip";
import WatchlistHeatmap from "../components/widgets/WatchlistHeatmap";
import SignalBoard from "../components/widgets/SignalBoard";
import AlertsFeed from "../components/widgets/AlertsFeed";
import PriceLine from "../components/charts/PriceLine";

export default function Overview() {
  const fetchFn = useCallback(() => fetchOverview(), []);
  const { data, loading, error } = usePolling(fetchFn, 60_000);

  if (loading && !data) return <LoadingState />;

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400 text-sm">{error}</p>
        <p className="text-gray-500 text-xs mt-1">
          The API server may not be running. Check that the backend is available at localhost:8000.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Market Overview</h2>

      {/* Key benchmark prices strip */}
      <KeyPricesStrip prices={data?.key_prices} />

      {/* Watchlist heatmap */}
      <WatchlistHeatmap watchlist={data?.watchlist} />

      {/* Two-column: Signals + Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SignalBoard signals={data?.signals} />
        <AlertsFeed alerts={data?.recent_alerts} />
      </div>

      {/* Coal price trend chart */}
      <PriceLine
        title="Coal Price Trend"
        data={data?.coal_price_trend}
        xKey="date"
        yKey="price"
        height={320}
      />
    </div>
  );
}
