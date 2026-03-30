import DataTable from "../components/common/DataTable";
import { formatNumber } from "../utils/formatters";

const tradeColumns = [
  { key: "exporter", label: "Exporter" },
  { key: "importer", label: "Importer" },
  { key: "volume_mt", label: "Volume (MT)", align: "right", format: (v) => formatNumber(v) },
  { key: "coal_type", label: "Type" },
  { key: "period", label: "Period" },
];

// Placeholder data for demonstration
const placeholderData = [
  { exporter: "Australia", importer: "Japan", volume_mt: 56_200_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "Australia", importer: "South Korea", volume_mt: 28_400_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "Indonesia", importer: "China", volume_mt: 98_700_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "Indonesia", importer: "India", volume_mt: 72_300_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "Russia", importer: "China", volume_mt: 45_100_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "South Africa", importer: "India", volume_mt: 18_600_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "Colombia", importer: "Europe", volume_mt: 12_900_000, coal_type: "Thermal", period: "2025 Q4" },
  { exporter: "USA", importer: "Europe", volume_mt: 8_400_000, coal_type: "Met", period: "2025 Q4" },
];

export default function TradeFlows() {
  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Trade Flows</h2>

      {/* Placeholder map */}
      <div className="card">
        <div className="card-header">Global Trade Flow Map</div>
        <div className="flex flex-col items-center justify-center py-12">
          {/* Simplified world map SVG outline */}
          <svg
            viewBox="0 0 800 400"
            className="w-full max-w-3xl opacity-20"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
          >
            {/* North America */}
            <path d="M120,80 L180,60 L220,80 L240,120 L220,180 L180,200 L160,220 L140,200 L100,160 L80,120 Z" className="text-gray-500" />
            {/* South America */}
            <path d="M180,220 L200,240 L220,300 L200,360 L180,380 L160,340 L150,280 L160,240 Z" className="text-gray-500" />
            {/* Europe */}
            <path d="M360,60 L400,50 L440,60 L460,100 L440,120 L400,130 L360,120 L350,80 Z" className="text-gray-500" />
            {/* Africa */}
            <path d="M380,140 L420,130 L460,160 L460,240 L440,300 L400,320 L380,280 L360,220 L360,160 Z" className="text-gray-500" />
            {/* Asia */}
            <path d="M480,40 L580,30 L660,60 L700,100 L680,160 L620,180 L560,160 L500,140 L480,100 Z" className="text-gray-500" />
            {/* Australia */}
            <path d="M620,260 L680,240 L720,260 L720,300 L680,320 L640,300 L620,280 Z" className="text-gray-500" />
          </svg>
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm font-medium">Trade Flow Map</p>
            <p className="text-gray-600 text-xs mt-1">Interactive visualization coming soon</p>
          </div>
        </div>
      </div>

      {/* Trade flow data table */}
      <div className="card">
        <div className="card-header">Trade Flow Data</div>
        <DataTable columns={tradeColumns} data={placeholderData} />
      </div>
    </div>
  );
}
