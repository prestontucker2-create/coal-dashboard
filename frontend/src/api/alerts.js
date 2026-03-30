import client from "./client";

export function fetchAlertConfigs() {
  return client.get("/alerts/configs");
}

export function createAlert(config) {
  return client.post("/alerts/configs", config);
}

export function updateAlert(id, updates) {
  return client.patch(`/alerts/configs/${id}`, updates);
}

export function deleteAlert(id) {
  return client.delete(`/alerts/configs/${id}`);
}

export function fetchAlertHistory(limit = 100) {
  return client.get("/alerts/history", { params: { limit } });
}
