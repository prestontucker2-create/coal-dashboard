import client from "./client";

export function fetchNews(timeframe, limit = 50) {
  return client.get("/sentiment/news", {
    params: { timeframe, limit },
  });
}

export function fetchReddit(timeframe) {
  return client.get("/sentiment/reddit", { params: { timeframe } });
}

export function fetchShortInterest(tickers) {
  return client.get("/sentiment/short-interest", {
    params: { tickers: tickers.join(",") },
  });
}
