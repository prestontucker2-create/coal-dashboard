import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { CHART_COLORS } from "../../utils/colors";

/**
 * AreaStack - Recharts stacked area chart.
 *
 * Props:
 *   data   - Array of objects
 *   xKey   - Key for x-axis (default "date")
 *   areas  - Array of { key, color?, label }
 *   height - Chart height (default 300)
 *   title  - Optional chart title
 */
export default function AreaStack({
  data,
  xKey = "date",
  areas,
  height = 300,
  title,
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

  const areaConfigs = areas || [{ key: "value", color: CHART_COLORS[0], label: "Value" }];

  return (
    <div className="card">
      {title && <div className="card-header">{title}</div>}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            tickLine={false}
            axisLine={{ stroke: "#374151" }}
          />
          <YAxis
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
          <Legend wrapperStyle={{ fontSize: "0.75rem", color: "#9ca3af" }} />
          {areaConfigs.map((area, i) => {
            const color = area.color || CHART_COLORS[i % CHART_COLORS.length];
            return (
              <Area
                key={area.key}
                type="monotone"
                dataKey={area.key}
                stackId="1"
                stroke={color}
                fill={color}
                fillOpacity={0.3}
                name={area.label || area.key}
              />
            );
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
