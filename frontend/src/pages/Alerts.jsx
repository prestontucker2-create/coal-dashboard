import { useCallback, useState } from "react";
import usePolling from "../hooks/usePolling";
import {
  fetchAlertConfigs,
  createAlert,
  updateAlert,
  deleteAlert,
  fetchAlertHistory,
} from "../api/alerts";
import LoadingState from "../components/common/LoadingState";
import DataTable from "../components/common/DataTable";
import { formatTimestamp } from "../utils/formatters";

export default function Alerts() {
  const [showForm, setShowForm] = useState(false);

  const configsFn = useCallback(() => fetchAlertConfigs(), []);
  const historyFn = useCallback(() => fetchAlertHistory(100), []);

  const configs = usePolling(configsFn, 30_000);
  const history = usePolling(historyFn, 30_000);

  const isLoading = configs.loading && !configs.data;

  if (isLoading) return <LoadingState />;

  const handleToggle = async (alert) => {
    try {
      await updateAlert(alert.id, { enabled: !alert.enabled });
      configs.refresh();
    } catch (err) {
      console.error("Failed to toggle alert:", err);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteAlert(id);
      configs.refresh();
    } catch (err) {
      console.error("Failed to delete alert:", err);
    }
  };

  const handleCreate = async (config) => {
    try {
      await createAlert(config);
      configs.refresh();
      setShowForm(false);
    } catch (err) {
      console.error("Failed to create alert:", err);
    }
  };

  const alertColumns = [
    { key: "name", label: "Name" },
    { key: "domain", label: "Domain" },
    { key: "condition", label: "Condition" },
    { key: "threshold", label: "Threshold", align: "right" },
    {
      key: "enabled",
      label: "Status",
      format: (v, row) => (
        <button
          onClick={() => handleToggle(row)}
          className={`text-xs font-medium px-2 py-0.5 rounded ${
            v
              ? "bg-green-900/40 text-green-400"
              : "bg-gray-700 text-gray-500"
          }`}
        >
          {v ? "Active" : "Disabled"}
        </button>
      ),
    },
    {
      key: "id",
      label: "",
      format: (v) => (
        <button
          onClick={() => handleDelete(v)}
          className="text-xs text-red-400 hover:text-red-300 transition-colors"
        >
          Delete
        </button>
      ),
    },
  ];

  const historyColumns = [
    { key: "triggered_at", label: "Time", format: (v) => formatTimestamp(v) },
    { key: "alert_name", label: "Alert" },
    { key: "domain", label: "Domain" },
    { key: "message", label: "Message" },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-gray-100">Alerts</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-100 bg-amber-600 rounded-md hover:bg-amber-500 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Alert
        </button>
      </div>

      {/* Alert creation form */}
      {showForm && (
        <AlertForm onSubmit={handleCreate} onCancel={() => setShowForm(false)} />
      )}

      {/* Alert configs table */}
      <div className="card">
        <div className="card-header">Alert Configurations</div>
        <DataTable columns={alertColumns} data={configs.data} />
      </div>

      {/* Alert history */}
      <div className="card">
        <div className="card-header">Alert History</div>
        <DataTable columns={historyColumns} data={history.data} />
      </div>
    </div>
  );
}

function AlertForm({ onSubmit, onCancel }) {
  const [form, setForm] = useState({
    name: "",
    domain: "pricing",
    condition: "above",
    metric: "",
    threshold: "",
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      ...form,
      threshold: Number(form.threshold),
      enabled: true,
    });
  };

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <div className="card-header">New Alert</div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">Name</label>
          <input
            type="text"
            value={form.name}
            onChange={update("name")}
            required
            placeholder="e.g. Newcastle above $150"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-amber-500"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Domain</label>
          <select
            value={form.domain}
            onChange={update("domain")}
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-amber-500"
          >
            <option value="pricing">Pricing</option>
            <option value="supply">Supply</option>
            <option value="demand">Demand</option>
            <option value="company">Company</option>
            <option value="macro">Macro</option>
            <option value="weather">Weather</option>
            <option value="sentiment">Sentiment</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Metric</label>
          <input
            type="text"
            value={form.metric}
            onChange={update("metric")}
            required
            placeholder="e.g. newcastle_price"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-amber-500"
          />
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Condition</label>
          <select
            value={form.condition}
            onChange={update("condition")}
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-amber-500"
          >
            <option value="above">Above</option>
            <option value="below">Below</option>
            <option value="change_pct_above">% Change Above</option>
            <option value="change_pct_below">% Change Below</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-400 mb-1">Threshold</label>
          <input
            type="number"
            step="any"
            value={form.threshold}
            onChange={update("threshold")}
            required
            placeholder="e.g. 150.00"
            className="w-full bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-md px-3 py-2 focus:outline-none focus:border-amber-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 pt-2">
        <button
          type="submit"
          className="px-4 py-2 text-sm font-medium text-gray-100 bg-amber-600 rounded-md hover:bg-amber-500 transition-colors"
        >
          Create Alert
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-400 bg-gray-800 rounded-md hover:bg-gray-700 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
