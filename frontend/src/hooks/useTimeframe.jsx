import { createContext, useContext, useState, useMemo } from "react";
import { TIMEFRAMES } from "../utils/constants";

const TimeframeContext = createContext(null);

export function TimeframeProvider({ children }) {
  const [timeframe, setTimeframe] = useState("3M");

  const value = useMemo(
    () => ({ timeframe, setTimeframe, timeframes: TIMEFRAMES }),
    [timeframe],
  );

  return (
    <TimeframeContext.Provider value={value}>
      {children}
    </TimeframeContext.Provider>
  );
}

export function useTimeframe() {
  const ctx = useContext(TimeframeContext);
  if (!ctx) {
    throw new Error("useTimeframe must be used within a TimeframeProvider");
  }
  return ctx;
}
