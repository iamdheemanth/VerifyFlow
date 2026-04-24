"use client";

import { useMemo, useState } from "react";

import type { ConfigurationComparison } from "@/types/run";

type ConfigsClientProps = {
  configs: ConfigurationComparison[];
};

type ActiveTab = "all" | "executor" | "judge";
type SortDir = "asc" | "desc";

function rateColor(value: number) {
  if (value >= 0.8) {
    return "bg-[#166534]";
  }

  if (value >= 0.6) {
    return "bg-[#B45309]";
  }

  return "bg-[#991B1B]";
}

function MetricBar({
  value,
  max = 1,
}: {
  value: number;
  max?: number;
}) {
  const normalized = max === 0 ? 0 : Math.max(0, Math.min(100, (value / max) * 100));

  return (
    <div className="w-12 h-1 rounded-full bg-[#E2DAD0] mt-1">
      <div
        style={{ width: `${normalized}%` }}
        className={`h-full rounded-full ${rateColor(value)}`}
      />
    </div>
  );
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function ConfigsClient({ configs }: ConfigsClientProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>("all");
  const [sortKey, setSortKey] =
    useState<keyof ConfigurationComparison>("success_rate");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const filteredConfigs = useMemo(() => {
    const scoped =
      activeTab === "all"
        ? configs
        : configs.filter((config) => config.role === activeTab);

    return [...scoped].sort((a, b) => {
      const aValue = a[sortKey];
      const bValue = b[sortKey];

      let result = 0;

      if (typeof aValue === "number" && typeof bValue === "number") {
        result = aValue - bValue;
      } else {
        result = String(aValue).localeCompare(String(bValue));
      }

      return sortDir === "asc" ? result : -result;
    });
  }, [activeTab, configs, sortDir, sortKey]);

  function handleSort(nextKey: keyof ConfigurationComparison) {
    if (sortKey === nextKey) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }

    setSortKey(nextKey);
    setSortDir("desc");
  }

  function sortLabel(label: string, key: keyof ConfigurationComparison) {
    if (sortKey !== key) {
      return label;
    }

    return `${label} ${sortDir === "asc" ? "↑" : "↓"}`;
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-[#F5F4F0]">
          Model Configurations
        </h1>
        <p className="mt-1 text-sm text-[#6F6D66]">
          Compare executor and judge performance across runs.
        </p>
      </div>

      <div className="flex border-b border-[#2A2A26] mb-6 mt-6">
        {(["all", "executor", "judge"] as const).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab
                ? "border-b-2 border-[#1A1410] text-[#F5F4F0] font-medium -mb-px"
                : "text-[#6F6D66] hover:text-[#8A8880]"
            }`}
          >
            {tab === "all"
              ? "All"
              : tab === "executor"
                ? "Executor"
                : "Judge"}
          </button>
        ))}
      </div>

      {configs.length === 0 ? (
        <div className="rounded-2xl border border-[#2A2A26] bg-[#141412] py-16 text-center shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
          <p className="text-sm text-[#6F6D66]">No configurations recorded yet.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-2xl border border-[#2A2A26] bg-[#141412] shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
          <table className="w-full text-sm">
            <thead className="bg-[#10100E]">
              <tr>
                {[
                  ["Name", "name"],
                  ["Model", "model_name"],
                  ["Version", "prompt_version"],
                  ["Role", "role"],
                  ["Runs", "run_count"],
                  ["Success Rate", "success_rate"],
                  ["Escalation Rate", "escalation_rate"],
                  ["Avg Confidence", "average_confidence"],
                  ["Avg Cost", "average_cost_usd"],
                ].map(([label, key]) => (
                  <th
                    key={key}
                    onClick={() => handleSort(key as keyof ConfigurationComparison)}
                    className="cursor-pointer select-none px-4 py-3 text-left text-[10px] uppercase tracking-widest text-[#6F6D66] hover:text-[#8A8880]"
                  >
                    {sortLabel(label, key as keyof ConfigurationComparison)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2A2A26]">
              {filteredConfigs.map((config) => (
                <tr
                  key={config.config_id}
                  className="transition-colors hover:bg-[#10100E]"
                >
                  <td className="px-4 py-3.5 font-medium text-[#F5F4F0]">
                    {config.name}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-xs text-[#8A8880]">
                    {config.model_name}
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="rounded bg-[#23231F] px-2 py-0.5 text-[10px] text-[#8A8880]">
                      {config.prompt_version}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                        config.role === "executor"
                          ? "bg-[#DBEAFE] text-[#1E40AF]"
                          : "bg-[#EDE9FE] text-[#4C1D95]"
                      }`}
                    >
                      {config.role === "executor" ? "Executor" : "Judge"}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[#8A8880]">
                    {config.run_count}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="text-[#F5F4F0]">
                      {formatPercent(config.success_rate)}
                      <MetricBar value={config.success_rate} />
                    </div>
                  </td>
                  <td
                    className={`px-4 py-3.5 ${
                      config.escalation_rate > 0.15
                        ? "text-[#991B1B]"
                        : "text-[#F5F4F0]"
                    }`}
                  >
                    {formatPercent(config.escalation_rate)}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="text-[#F5F4F0]">
                      {formatPercent(config.average_confidence)}
                      <MetricBar value={config.average_confidence} />
                    </div>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-[#8A8880]">
                    ${config.average_cost_usd.toFixed(4)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

