import client from "./client";

export function fetchBenchmarks(timeframe) {
  return client.get("/pricing/benchmarks", { params: { timeframe } });
}

export function fetchLatestPrices() {
  return client.get("/pricing/latest");
}

export function fetchSpreads(timeframe) {
  return client.get("/pricing/spreads", { params: { timeframe } });
}

export function fetchGas(timeframe) {
  return client.get("/pricing/gas", { params: { timeframe } });
}
