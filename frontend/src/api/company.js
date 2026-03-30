import client from "./client";

export function fetchPrices(tickers, timeframe) {
  return client.get("/company/prices", {
    params: { tickers: tickers.join(","), timeframe },
  });
}

export function fetchLatest() {
  return client.get("/company/latest");
}

export function fetchPeerComparison(tickers) {
  return client.get("/company/peers", {
    params: { tickers: tickers.join(",") },
  });
}

export function fetchFinancials(ticker) {
  return client.get(`/company/${ticker}/financials`);
}

export function fetchInsiderTransactions(ticker, timeframe) {
  return client.get(`/company/${ticker}/insiders`, {
    params: { timeframe },
  });
}

export function fetchShortInterest(ticker, timeframe) {
  return client.get(`/company/${ticker}/short-interest`, {
    params: { timeframe },
  });
}
