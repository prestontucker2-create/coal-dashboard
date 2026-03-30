import client from "./client";

export function fetchDegreeDays(timeframe) {
  return client.get("/weather/degree-days", { params: { timeframe } });
}

export function fetchEnso() {
  return client.get("/weather/enso");
}

export function fetchRainfall(region, timeframe) {
  return client.get("/weather/rainfall", {
    params: { region, timeframe },
  });
}
