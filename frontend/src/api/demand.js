import client from "./client";

export function fetchGeneration(region, timeframe) {
  return client.get("/demand/generation", {
    params: { region, timeframe },
  });
}

export function fetchSteel(timeframe) {
  return client.get("/demand/steel", { params: { timeframe } });
}

export function fetchSummary() {
  return client.get("/demand/summary");
}
