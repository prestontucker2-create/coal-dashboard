import { formatTimestamp } from "../../utils/formatters";

/**
 * AlertsFeed - Scrollable list of recent alerts.
 *
 * Props:
 *   alerts - Array of { message, triggered_at, domain }
 */
export default function AlertsFeed({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Recent Alerts</div>
        <div className="text-sm text-gray-500 text-center py-6">
          No recent alerts
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">Recent Alerts</div>
      <div className="max-h-80 overflow-y-auto space-y-2 scrollbar-thin">
        {alerts.map((alert, i) => (
          <div
            key={i}
            className="flex items-start gap-3 px-3 py-2 bg-gray-800/40 rounded-md animate-fade-in"
          >
            {/* Domain badge */}
            <span className="text-[10px] font-medium text-amber-400 bg-amber-900/30 px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5">
              {alert.domain || "system"}
            </span>

            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-300 leading-relaxed">
                {alert.message}
              </p>
              <span className="text-[10px] text-gray-600 mt-0.5 block">
                {formatTimestamp(alert.triggered_at)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
