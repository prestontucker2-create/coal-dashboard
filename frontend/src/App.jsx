import { Routes, Route } from "react-router-dom";
import { TimeframeProvider } from "./hooks/useTimeframe";
import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";

import Overview from "./pages/Overview";
import Pricing from "./pages/Pricing";
import Supply from "./pages/Supply";
import Demand from "./pages/Demand";
import TradeFlows from "./pages/TradeFlows";
import Macro from "./pages/Macro";
import CompanyDeepDive from "./pages/CompanyDeepDive";
import Weather from "./pages/Weather";
import Sentiment from "./pages/Sentiment";
import Alerts from "./pages/Alerts";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <TimeframeProvider>
      <div className="flex h-screen overflow-hidden">
        {/* Fixed sidebar */}
        <Sidebar />

        {/* Main content area */}
        <div className="flex flex-col flex-1 min-w-0">
          <Header />

          <main className="flex-1 overflow-y-auto p-6 scrollbar-thin">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/supply" element={<Supply />} />
              <Route path="/demand" element={<Demand />} />
              <Route path="/trade-flows" element={<TradeFlows />} />
              <Route path="/macro" element={<Macro />} />
              <Route path="/company" element={<CompanyDeepDive />} />
              <Route path="/company/:ticker" element={<CompanyDeepDive />} />
              <Route path="/weather" element={<Weather />} />
              <Route path="/sentiment" element={<Sentiment />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </TimeframeProvider>
  );
}
