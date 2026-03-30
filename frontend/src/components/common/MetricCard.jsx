import clsx from "clsx";
import { formatPct } from "../../utils/formatters";
import { getChangeColor } from "../../utils/colors";

/**
 * MetricCard - displays a single KPI metric.
 *
 * Props:
 *   label       - Metric name (e.g. "Newcastle Coal")
 *   value       - Formatted display value (e.g. "$142.50")
 *   delta       - Numeric % change (e.g. -1.23)
 *   sparkData   - Optional array of numbers for a mini sparkline
 *   source      - Data source attribution (e.g. "ICE Futures")
 *   timestamp   - Last update time string
 *   className   - Additional CSS classes
 */
export default function MetricCard({
  label,
  value,
  delta,
  sparkData,
  source,
  timestamp,
  className,
}) {
  const pct = formatPct(delta);
  const changeColor = getChangeColor(delta);

  return (
    <div
      className={clsx(
        "bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-1",
        className,
      )}
    >
      {/* Label */}
      <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
        {label}
      </span>

      {/* Value + Delta */}
      <div className="flex items-baseline gap-2">
        <span className="text-xl font-bold text-gray-100">{value ?? "--"}</span>
        {delta != null && (
          <span
            className="text-sm font-semibold"
            style={{ color: changeColor }}
          >
            {pct.text}
          </span>
        )}
      </div>

      {/* Mini sparkline */}
      {sparkData && sparkData.length > 1 && (
        <MiniSparkline data={sparkData} color={changeColor} />
      )}

      {/* Source + timestamp */}
      {(source || timestamp) && (
        <div className="flex items-center gap-2 mt-1">
          {source && (
            <span className="text-[10px] text-gray-600">{source}</span>
          )}
          {timestamp && (
            <span className="text-[10px] text-gray-600">{timestamp}</span>
          )}
        </div>
      )}
    </div>
  );
}

/** Tiny SVG sparkline */
function MiniSparkline({ data, color }) {
  const width = 80;
  const height = 24;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="mt-1">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
