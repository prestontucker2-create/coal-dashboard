import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Custom hook that polls a fetch function on an interval.
 * Pauses when the document tab is hidden.
 *
 * @param {Function} fetchFn  - Async function to call
 * @param {number}   intervalMs - Polling interval in milliseconds
 * @param {Array}    deps       - Extra dependencies that trigger a re-fetch
 * @returns {{ data, loading, error, refresh }}
 */
export default function usePolling(fetchFn, intervalMs = 60_000, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const fetchRef = useRef(fetchFn);

  // Keep fetchFn ref up to date without triggering effect
  useEffect(() => {
    fetchRef.current = fetchFn;
  }, [fetchFn]);

  const refresh = useCallback(async () => {
    try {
      setLoading((prev) => (prev ? true : prev)); // keep true on first load
      setError(null);
      const result = await fetchRef.current();
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to fetch");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + interval
  useEffect(() => {
    refresh();

    const startPolling = () => {
      stopPolling();
      intervalRef.current = setInterval(refresh, intervalMs);
    };

    const stopPolling = () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };

    const handleVisibility = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        refresh();
        startPolling();
      }
    };

    startPolling();
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      stopPolling();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, refresh, ...deps]);

  return { data, loading, error, refresh };
}
