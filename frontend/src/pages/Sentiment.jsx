import { useCallback } from "react";
import { useTimeframe } from "../hooks/useTimeframe";
import usePolling from "../hooks/usePolling";
import { fetchNews, fetchShortInterest } from "../api/sentiment";
import { TICKERS } from "../utils/constants";
import LoadingState from "../components/common/LoadingState";
import DataTable from "../components/common/DataTable";
import { formatDate, formatPct, formatNumber } from "../utils/formatters";
import { getChangeColor } from "../utils/colors";

const shortColumns = [
  { key: "ticker", label: "Ticker" },
  { key: "short_interest", label: "Short Interest", align: "right", format: (v) => formatNumber(v) },
  { key: "short_pct_float", label: "% of Float", align: "right", format: (v) => {
    const p = formatPct(v);
    return <span style={{ color: p.color === "green" ? "#22c55e" : p.color === "red" ? "#ef4444" : "#6b7280" }}>{p.text}</span>;
  }},
  { key: "days_to_cover", label: "Days to Cover", align: "right" },
];

export default function Sentiment() {
  const { timeframe } = useTimeframe();

  const newsFn = useCallback(() => fetchNews(timeframe, 50), [timeframe]);
  const shortFn = useCallback(() => fetchShortInterest(TICKERS), []);

  const news = usePolling(newsFn, 120_000, [timeframe]);
  const short = usePolling(shortFn, 300_000);

  const isLoading = news.loading && !news.data;

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6 animate-fade-in">
      <h2 className="text-xl font-bold text-gray-100">Sentiment</h2>

      {/* News feed */}
      <div className="card">
        <div className="card-header">News Feed</div>
        <div className="space-y-2 max-h-[500px] overflow-y-auto scrollbar-thin">
          {news.data && Array.isArray(news.data) && news.data.length > 0 ? (
            news.data.map((article, i) => (
              <NewsItem key={i} article={article} />
            ))
          ) : (
            <div className="text-sm text-gray-500 text-center py-6">
              No news articles available
            </div>
          )}
        </div>
      </div>

      {/* Short interest table */}
      <div className="card">
        <div className="card-header">Short Interest - Watchlist</div>
        <DataTable columns={shortColumns} data={short.data} />
      </div>
    </div>
  );
}

function NewsItem({ article }) {
  const sentimentColor = article.sentiment_score != null
    ? getChangeColor(article.sentiment_score)
    : "#6b7280";

  return (
    <div className="flex items-start gap-3 px-3 py-2.5 bg-gray-800/30 rounded-md hover:bg-gray-800/50 transition-colors">
      {/* Sentiment dot */}
      <div
        className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5"
        style={{ backgroundColor: sentimentColor }}
      />

      <div className="flex-1 min-w-0">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm text-gray-200 hover:text-amber-400 transition-colors line-clamp-2 font-medium"
        >
          {article.headline || article.title}
        </a>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-[10px] text-gray-500">{article.source}</span>
          <span className="text-[10px] text-gray-600">{formatDate(article.published_at || article.date)}</span>
          {article.sentiment_label && (
            <span
              className="text-[10px] font-medium px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: `${sentimentColor}22`,
                color: sentimentColor,
              }}
            >
              {article.sentiment_label}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
