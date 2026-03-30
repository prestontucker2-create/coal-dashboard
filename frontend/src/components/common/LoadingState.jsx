import clsx from "clsx";

/**
 * LoadingState - skeleton / spinner for loading states.
 *
 * Props:
 *   variant  - "spinner" | "skeleton" (default "spinner")
 *   rows     - Number of skeleton rows (for skeleton variant)
 *   className - Additional CSS classes
 */
export default function LoadingState({ variant = "spinner", rows = 3, className }) {
  if (variant === "skeleton") {
    return (
      <div className={clsx("space-y-3 animate-pulse", className)}>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-3">
            <div className="h-4 bg-gray-800 rounded w-1/4" />
            <div className="h-4 bg-gray-800 rounded w-1/2" />
            <div className="h-4 bg-gray-800 rounded w-1/4" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={clsx("flex items-center justify-center py-12", className)}>
      <div className="flex flex-col items-center gap-3">
        <svg
          className="w-8 h-8 text-amber-500 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <span className="text-xs text-gray-500">Loading...</span>
      </div>
    </div>
  );
}
