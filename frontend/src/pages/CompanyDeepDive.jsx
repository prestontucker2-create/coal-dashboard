import { useCallback, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import {
  fetchPrices,
  fetchFinancials,
  fetchInsiderTransactions,
  fetchShortInterest,
} from "../api/company";
import { TICKERS } from "../utils/constants";
import LoadingState from "../components/common/LoadingState";
import PriceLine from "../components/charts/PriceLine";
import MetricCard from "../components/common/MetricCard";
import DataTable from "../components/common/DataTable";
import { formatPrice, formatNumber, formatPct, formatDate } from "../utils/formatters";

const financialColumns = [
  { key: "metric", label: "Metric" },
  { key: "value", label: "Value", align: "right", format: (v) => formatNumber(v) },
  { key: "period", label: "Period" },
];

const insiderColumns = [
  { key: "date", label: "Date", format: (v) => formatDate(v) },
  { key: "insider", label: "Insider" },
  { key: "type", label: "Type" },
  { key: "shares", label: "Shares", align: "right", format: (v) => formatNumber(v) },
  { key: "price", label: "Price", align: "right", format: (v) => formatPrice(v) },
];

const shortColumns = [
  { key: "date", label: "Date", format: (v) => formatDate(v) },
  { key: "short_interest", label: "Short Interest", align: "right", format: (v) => formatNumber(v) },
  { key: "short_pct_float", label: "% of Float", align: "right", format: (v) => {
    const p = formatPct(v);
    return p.text;
  }},
  { key: "days_to_cover", label: "Days to Cover", align: "right" },
];

export default function CompanyDeepDive() {
  const { ticker: urlTicker } = useParams();
  const navigate = useNavigate();
  const { timeframe } = useTimeframe();
  const [selectedTicker, setSelectedTicker] = useState(urlTicker || "BTU");

  const activeTicker = urlTicker || selectedTicker;

  const handleTickerChange = (e) => {
    const t = e.target.value;
    setSelectedTicker(t);
    navigate(`/company/${t}`);
  };

  const pricesFn = useCallback(
    () => fetchPrices([activeTicker], timeframe),
    [activeTicker, timeframe],
  );
  const financialsFn = useCallback(
    () => fetchFinancials(activeTicker),
    [activeTicker],
  );
  const insidersFn = useCallback(
    () => fetchInsiderTransactions(activeTicker, timeframe),
    [activeTicker, timeframe],
  );
  const shortFn = useCallback(
    () => fetchShortInterest(activeTicker, timeframe),
    [activeTicker, timeframe],
  );

  const prices = usePolling(pricesFn, 120_000, [activeTicker, timeframe]);
  const financials = usePolling(financialsFn, 300_000, [activeTicker]);
  const insiders = usePolling(insidersFn, 300_000, [activeTicker, timeframe]);
  const short = usePolling(shortFn, 300_000, [activeTicker, timeframe]);

  const isLoading = prices.loading && !prices.data;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Ticker selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-100">Company Deep Dive</h2>
        <select
          value={activeTicker}
          onChange={handleTickerChange}
          className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-1.5 focus:outline-none focus:border-amber-500"
        >
          {TICKERS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <LoadingState />
      ) : (
        <>
          {/* Stock price chart */}
          <PriceLine
            title={`${activeTicker} Stock Price`}
            data={prices.data}
            xKey="date"
            yKey="close"
            height={350}
          />

          {/* Key financials grid */}
          {financials.data && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
                Key Financials
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {(Array.isArray(financials.data)
                  ? financials.data.slice(0, 8)
                  : Object.entries(financials.data).slice(0, 8).map(([k, v]) => ({
                      metric: k,
                      value: v?.value ?? v,
                      change_pct: v?.change_pct,
                    }))
                ).map((item, i) => (
                  <MetricCard
                    key={i}
                    label={item.metric || item.label || item.name}
                    value={formatNumber(item.value)}
                    delta={item.change_pct}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Financials table */}
          {financials.data && Array.isArray(financials.data) && (
            <div className="card">
              <div className="card-header">Financial Data</div>
              <DataTable columns={financialColumns} data={financials.data} />
            </div>
          )}

          {/* Insider transactions */}
          <div className="card">
            <div className="card-header">Insider Transactions</div>
            {insiders.data && Array.isArray(insiders.data) && insiders.data.length > 0 ? (
              <DataTable columns={insiderColumns} data={insiders.data} />
            ) : (
              <div className="text-sm text-gray-500 text-center py-4">
                No insider transaction data available
              </div>
            )}
          </div>

          {/* Short interest */}
          <div className="card">
            <div className="card-header">Short Interest</div>
            {short.data && Array.isArray(short.data) && short.data.length > 0 ? (
              <DataTable columns={shortColumns} data={short.data} />
            ) : (
              <div className="text-sm text-gray-500 text-center py-4">
                No short interest data available
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
