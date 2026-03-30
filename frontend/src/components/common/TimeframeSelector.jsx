import clsx from "clsx";
import { useTimeframe } from "../../hooks/useTimeframe";

export default function TimeframeSelector() {
  const { timeframe, setTimeframe, timeframes } = useTimeframe();

  return (
    <div className="flex items-center bg-gray-800 rounded-md p-0.5">
      {timeframes.map((tf) => (
        <button
          key={tf}
          onClick={() => setTimeframe(tf)}
          className={clsx(
            "px-2.5 py-1 text-xs font-medium rounded transition-colors",
            tf === timeframe
              ? "bg-amber-600 text-white"
              : "text-gray-400 hover:text-gray-200",
          )}
        >
          {tf}
        </button>
      ))}
    </div>
  );
}
