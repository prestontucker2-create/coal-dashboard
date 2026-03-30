/** Bullish / positive signal color */
export const BULL_COLOR = "#22c55e"; // green-500

/** Bearish / negative signal color */
export const BEAR_COLOR = "#ef4444"; // red-500

/** Neutral / unchanged color */
export const NEUTRAL_COLOR = "#6b7280"; // gray-500

/** Chart line colors for multi-series */
export const CHART_COLORS = [
  "#3b82f6", // blue-500
  "#f59e0b", // amber-500
  "#8b5cf6", // violet-500
  "#06b6d4", // cyan-500
  "#ec4899", // pink-500
  "#10b981", // emerald-500
  "#f97316", // orange-500
  "#6366f1", // indigo-500
  "#14b8a6", // teal-500
];

/**
 * Returns a CSS color based on the sign of a percentage change.
 * @param {number} pct
 * @returns {string} hex color
 */
export function getChangeColor(pct) {
  if (pct == null || isNaN(pct) || pct === 0) return NEUTRAL_COLOR;
  return pct > 0 ? BULL_COLOR : BEAR_COLOR;
}

/**
 * Heatmap scale from deep red (index 0) to deep green (index 9).
 * Index 4-5 is the neutral midpoint.
 */
export const HEATMAP_SCALE = [
  "#991b1b", // red-800
  "#b91c1c", // red-700
  "#dc2626", // red-600
  "#ef4444", // red-500
  "#6b7280", // gray-500 (neutral)
  "#6b7280", // gray-500 (neutral)
  "#22c55e", // green-500
  "#16a34a", // green-600
  "#15803d", // green-700
  "#166534", // green-800
];

/**
 * Map a percentage value to a heatmap color.
 * @param {number} pct - value where 0 is neutral, positive is green, negative is red
 * @param {number} maxAbs - the absolute max for the scale (default 5)
 * @returns {string} hex color
 */
export function getHeatmapColor(pct, maxAbs = 5) {
  if (pct == null || isNaN(pct)) return HEATMAP_SCALE[4];
  const clamped = Math.max(-maxAbs, Math.min(maxAbs, pct));
  const normalized = (clamped + maxAbs) / (2 * maxAbs); // 0..1
  const index = Math.round(normalized * (HEATMAP_SCALE.length - 1));
  return HEATMAP_SCALE[index];
}
