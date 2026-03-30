import { format, parseISO } from "date-fns";

/**
 * Format a numeric value as a USD price string.
 * @param {number} value
 * @param {number} decimals
 * @returns {string} e.g. "$123.45"
 */
export function formatPrice(value, decimals = 2) {
  if (value == null || isNaN(value)) return "--";
  return `$${Number(value).toFixed(decimals)}`;
}

/**
 * Format a numeric value as a percentage with sign and color hint.
 * @param {number} value - Percentage value (e.g. 1.23 means 1.23%)
 * @param {number} decimals
 * @returns {{ text: string, color: string }}
 */
export function formatPct(value, decimals = 2) {
  if (value == null || isNaN(value)) return { text: "--", color: "gray" };
  const num = Number(value);
  const sign = num >= 0 ? "+" : "";
  const text = `${sign}${num.toFixed(decimals)}%`;
  const color = num > 0 ? "green" : num < 0 ? "red" : "gray";
  return { text, color };
}

/**
 * Format a large number with K/M/B suffixes.
 * @param {number} value
 * @returns {string} e.g. "1.2M", "456K", "3.4B"
 */
export function formatNumber(value) {
  if (value == null || isNaN(value)) return "--";
  const num = Number(value);
  const abs = Math.abs(num);

  if (abs >= 1_000_000_000) {
    return `${(num / 1_000_000_000).toFixed(1)}B`;
  }
  if (abs >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toFixed(0);
}

/**
 * Format a date string as "Mar 30, 2026".
 * @param {string} dateStr - ISO date string or parseable date
 * @returns {string}
 */
export function formatDate(dateStr) {
  if (!dateStr) return "--";
  try {
    const d = typeof dateStr === "string" ? parseISO(dateStr) : new Date(dateStr);
    return format(d, "MMM d, yyyy");
  } catch {
    return "--";
  }
}

/**
 * Format a timestamp as "Mar 30, 2026 14:30".
 * @param {string|number} ts - ISO string or unix timestamp
 * @returns {string}
 */
export function formatTimestamp(ts) {
  if (!ts) return "--";
  try {
    const d = typeof ts === "number" ? new Date(ts * 1000) : parseISO(ts);
    return format(d, "MMM d, yyyy HH:mm");
  } catch {
    return "--";
  }
}
