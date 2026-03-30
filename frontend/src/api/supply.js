import client from "./client";

export function fetchProduction(region, timeframe) {
  return client.get("/supply/production", {
    params: { region, timeframe },
  });
}

export function fetchInventories(timeframe) {
  return client.get("/supply/inventories", { params: { timeframe } });
}

export function fetchSummary() {
  return client.get("/supply/summary");
}
