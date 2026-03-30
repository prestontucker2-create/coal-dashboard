import client from "./client";

export function fetchIndicators(names, timeframe) {
  return client.get("/macro/indicators", {
    params: { names: names.join(","), timeframe },
  });
}

export function fetchLatest() {
  return client.get("/macro/latest");
}

export function fetchCot(timeframe) {
  return client.get("/macro/cot", { params: { timeframe } });
}
