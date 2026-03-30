import client from "./client";

export function fetchHealth() {
  return client.get("/system/health");
}

export function fetchFreshness() {
  return client.get("/system/freshness");
}

export function triggerRefresh(domain) {
  return client.post("/system/refresh", { domain });
}
