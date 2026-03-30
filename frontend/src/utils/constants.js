/** Available timeframe options */
export const TIMEFRAMES = ["1W", "1M", "3M", "6M", "1Y", "3Y"];

/** All tracked coal equity tickers */
export const TICKERS = [
  "BTU",
  "WHC.AX",
  "CEIX",
  "CNXR",
  "HCC",
  "AMR",
  "ARLP",
  "TGA.L",
  "YAL.AX",
];

/** Default / primary tickers shown by default */
export const PRIMARY_TICKERS = ["BTU", "WHC.AX"];

/** Sidebar navigation domains */
export const DOMAINS = [
  { name: "Overview",     path: "/",            icon: "grid" },
  { name: "Pricing",      path: "/pricing",     icon: "dollar" },
  { name: "Supply",       path: "/supply",      icon: "truck" },
  { name: "Demand",       path: "/demand",      icon: "zap" },
  { name: "Trade Flows",  path: "/trade-flows", icon: "globe" },
  { name: "Macro",        path: "/macro",       icon: "trending" },
  { name: "Companies",    path: "/company",     icon: "building" },
  { name: "Weather",      path: "/weather",     icon: "cloud" },
  { name: "Sentiment",    path: "/sentiment",   icon: "message" },
  { name: "Alerts",       path: "/alerts",      icon: "bell" },
  { name: "Settings",     path: "/settings",    icon: "settings" },
];
