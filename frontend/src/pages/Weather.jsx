import { useCallback } from "react";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import { fetchDegreeDays, fetchEnso, fetchRainfall } from "../api/weather";
import LoadingState from "../components/common/LoadingState";
import PriceLine from "../components/charts/PriceLine";
import MetricCard from "../components/common/MetricCard";

export default function Weather() {
  const { timeframe } = useTimeframe();

  const hddFn = useCallback(() => fetchDegreeDays(timeframe), [timeframe]);
  const ensoFn = useCallback(() => fetchEnso(), []);
  const rainfallFn = useCallback(() => fetchRainfall("hunter_valley", timeframe), [timeframe]);

  const hdd = usePolling(hddFn, 300_000, [timeframe]);
  const enso = usePolling(ensoFn, 600_000);
  const rainfall = usePolling(rainfallFn, 300_000, [timeframe]);

  const isLoading = hdd.loading && !hdd.data;

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Weather</h2>

      {/* ENSO status card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <MetricCard
          label="ENSO Phase"
          value={enso.data?.phase || enso.data?.status || "--"}
          delta={enso.data?.oni_value}
          source="NOAA"
          timestamp={enso.data?.updated_at}
          className="md:col-span-1"
        />
        <MetricCard
          label="ONI Index"
          value={enso.data?.oni_value != null ? enso.data.oni_value.toFixed(2) : "--"}
          source="NOAA"
        />
        <MetricCard
          label="Forecast"
          value={enso.data?.forecast || "--"}
          source="NOAA"
        />
      </div>

      {/* Heating Degree Days */}
      <PriceLine
        title="Heating Degree Days (HDD)"
        data={hdd.data}
        xKey="date"
        yKey="hdd"
        height={300}
      />

      {/* Rainfall */}
      <PriceLine
        title="Hunter Valley Rainfall (mm)"
        data={rainfall.data}
        xKey="date"
        yKey="rainfall_mm"
        height={280}
      />
    </div>
  );
}
