import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30_000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Response interceptor: unwrap .data automatically
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      "An unexpected error occurred";

    console.error(`[API] ${error.config?.method?.toUpperCase()} ${error.config?.url} - ${message}`);
    return Promise.reject(new Error(message));
  },
);

export default client;
