import { useNavigate } from "react-router-dom";
import { formatPrice, formatPct } from "../../utils/formatters";
import { getHeatmapColor } from "../../utils/colors";

/**
 * WatchlistHeatmap - Grid of ticker cards colored by daily % change.
 *
 * Props:
 *   watchlist - Array of { ticker, price, change_pct }
 */
export default function WatchlistHeatmap({ watchlist }) {
  const navigate = useNavigate();

  if (!watchlist || watchlist.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Watchlist</div>
        <div className="text-sm text-gray-500 text-center py-6">
          No watchlist data available
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Watchlist Heatmap</div>
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
        {watchlist.map((item) => {
          const pct = formatPct(item.change_pct);
          const bgColor = getHeatmapColor(item.change_pct);

          return (
            <button
              key={item.ticker}
              onClick={() => navigate(`/company/${item.ticker}`)}
              className="rounded-lg p-3 text-center transition-transform hover:scale-105 cursor-pointer border border-gray-700/30"
              style={{ backgroundColor: `${bgColor}22`, borderColor: `${bgColor}44` }}
            >
              <div className="text-xs font-bold text-gray-200 truncate">
                {item.ticker}
              </div>
              <div className="text-sm font-semibold text-gray-100 mt-0.5">
                {formatPrice(item.price)}
              </div>
              <div
                className="text-xs font-medium mt-0.5"
                style={{ color: bgColor }}
              >
                {pct.text}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
