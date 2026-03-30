import clsx from "clsx";
import { BULL_COLOR, BEAR_COLOR } from "../../utils/colors";

/**
 * SignalBoard - Two-column layout of bull/bear signals.
 *
 * Props:
 *   signals - Array of { name, direction ("bull"|"bear"), strength (0-100), domain }
 */
export default function SignalBoard({ signals }) {
  if (!signals || signals.length === 0) {
    return (
      <div className="card">
        <div className="card-header">Signal Board</div>
        <div className="text-sm text-gray-500 text-center py-6">
          No signals available
        </div>
      </div>
    );
  }

  const bullSignals = signals.filter((s) => s.direction === "bull");
  const bearSignals = signals.filter((s) => s.direction === "bear");

  return (
    <div className="card">
      <div className="card-header">Signal Board</div>
      <div className="grid grid-cols-2 gap-4">
        {/* Bull column */}
        <div>
          <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wider mb-2">
            Bullish
          </h4>
          <div className="space-y-2">
            {bullSignals.length === 0 ? (
              <div className="text-xs text-gray-600">No bull signals</div>
            ) : (
              bullSignals.map((s, i) => (
                <SignalItem key={i} signal={s} color={BULL_COLOR} />
              ))
            )}
          </div>
        </div>

        {/* Bear column */}
        <div>
          <h4 className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-2">
            Bearish
          </h4>
          <div className="space-y-2">
            {bearSignals.length === 0 ? (
              <div className="text-xs text-gray-600">No bear signals</div>
            ) : (
              bearSignals.map((s, i) => (
                <SignalItem key={i} signal={s} color={BEAR_COLOR} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SignalItem({ signal, color }) {
  return (
    <div className="bg-gray-800/50 rounded-md px-3 py-2">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-300">{signal.name}</span>
        <span
          className={clsx(
            "text-[10px] font-medium px-1.5 py-0.5 rounded",
            signal.direction === "bull"
              ? "bg-green-900/40 text-green-400"
              : "bg-red-900/40 text-red-400",
          )}
        >
          {signal.domain}
        </span>
      </div>
      {/* Strength bar */}
      <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${Math.min(100, Math.max(0, signal.strength || 0))}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}
