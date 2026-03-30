import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { CHART_COLORS } from "../../utils/colors";

/**
 * PriceLine - Recharts line chart for time-series data.
 *
 * Props:
 *   data     - Array of objects (e.g. [{date, price}, ...])
 *   xKey     - Key for x-axis (default "date")
 *   yKey     - Key for single-line y-axis (default "price")
 *   lines    - Array of {key, color?, label} for multi-line. Overrides yKey.
 *   height   - Chart height in pixels (default 300)
 *   title    - Optional chart title
 *   yDomain  - Optional [min, max] for Y axis
 */
export default function PriceLine({
  data,
  xKey = "date",
  yKey = "price",
  lines,
  height = 300,
  title,
  yDomain,
}) {
  if (!data || data.length === 0) {
    return (
      <div className="card">
        {title && <div className="card-header">{title}</div>}
        <div className="flex items-center justify-center text-gray-500 text-sm" style={{ height }}>
          No chart data available
        </div>
      </div>
    );
  }

  const lineConfigs = lines || [{ key: yKey, color: CHART_COLORS[0], label: yKey }];

  return (
    <div className="card">
      {title && <div className="card-header">{title}</div>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#374151" }}
          />
          <YAxis
            domain={yDomain || ["auto", "auto"]}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#374151" }}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#111827",
              border: "1px solid #374151",
              borderRadius: "0.375rem",
              fontSize: "0.75rem",
            }}
            labelStyle={{ color: "#9ca3af" }}
            itemStyle={{ color: "#e5e7eb" }}
          />
          {lineConfigs.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: "0.75rem", color: "#9ca3af" }}
            />
          )}
          {lineConfigs.map((line, i) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              stroke={line.color || CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={1.5}
              dot={false}
              name={line.label || line.key}
              activeDot={{ r: 4, fill: line.color || CHART_COLORS[i % CHART_COLORS.length] }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
