import { useState, useMemo } from "react";
import clsx from "clsx";

/**
 * DataTable - sortable table component.
 *
 * Props:
 *   columns  - Array of { key, label, format?, align? }
 *   data     - Array of row objects
 *   className - Additional CSS classes
 */
export default function DataTable({ columns, data, className }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDir, setSortDir] = useState("asc");

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey || !data) return data || [];
    return [...data].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      const cmp = typeof aVal === "number" ? aVal - bVal : String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, sortKey, sortDir]);

  if (!data || data.length === 0) {
    return (
      <div className={clsx("text-sm text-gray-500 text-center py-8", className)}>
        No data available
      </div>
    );
  }

  return (
    <div className={clsx("overflow-x-auto", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800">
            {columns.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className={clsx(
                  "px-3 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-300 transition-colors select-none",
                  col.align === "right" ? "text-right" : "text-left",
                )}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  {sortKey === col.key && (
                    <span className="text-amber-500">
                      {sortDir === "asc" ? "\u2191" : "\u2193"}
                    </span>
                  )}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedData.map((row, i) => (
            <tr
              key={i}
              className={clsx(
                "border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors",
                i % 2 === 0 ? "bg-gray-900/30" : "bg-gray-950/30",
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={clsx(
                    "px-3 py-2 text-gray-300",
                    col.align === "right" && "text-right",
                  )}
                >
                  {col.format ? col.format(row[col.key], row) : (row[col.key] ?? "--")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
