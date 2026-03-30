import client from "./client";

export function fetchOverview() {
  return client.get("/overview");
}
