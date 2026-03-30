import MetricCard from "../common/MetricCard";
import { formatPrice } from "../../utils/formatters";

/**
 * KeyPricesStrip - Horizontal row of MetricCards for benchmark prices.
 *
 * Props:
 *   prices - Object with structure like:
 *     {
 *       newcastle: { value, change_pct, source },
 *       api2:     { value, change_pct, source },
 *       gas:      { value, change_pct, source },
 *       fx:       { value, change_pct, source },
 *     }
 */
export default function KeyPricesStrip({ prices }) {
  if (!prices) {
    return null;
  }

  const metrics = [
    { key: "newcastle",  label: "Newcastle 6000",   prefix: "$" },
    { key: "api2",       label: "API2 (Rotterdam)", prefix: "$" },
    { key: "api4",       label: "API4 (Richards Bay)", prefix: "$" },
    { key: "gas",        label: "Henry Hub Gas",     prefix: "$" },
    { key: "fx",         label: "AUD/USD",           prefix: "" },
  ];

  // Filter to only show metrics that exist in the data
  const available = metrics.filter((m) => prices[m.key]);

  if (available.length === 0) {
    // Fallback: render whatever keys are in the prices object
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {Object.entries(prices).map(([key, data]) => (
          <MetricCard
            key={key}
            label={key}
            value={formatPrice(data?.value ?? data?.price ?? data)}
            delta={data?.change_pct}
            source={data?.source}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {available.map((m) => {
        const d = prices[m.key];
        return (
          <MetricCard
            key={m.key}
            label={m.label}
            value={
              m.prefix === "$"
                ? formatPrice(d.value ?? d.price)
                : (d.value ?? d.price)?.toFixed(4)
            }
            delta={d.change_pct}
            source={d.source}
            timestamp={d.timestamp}
          />
        );
      })}
    </div>
  );
}
