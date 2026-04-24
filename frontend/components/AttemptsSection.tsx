"use client";

import { useState } from "react";

import StatusBadge from "@/components/StatusBadge";
import type { TaskAttempt } from "@/types/run";

type AttemptsSectionProps = {
  attempts: TaskAttempt[];
};

function formatLatency(totalLatencyMs: number | null) {
  if (totalLatencyMs === null) {
    return "—";
  }

  if (totalLatencyMs >= 1000) {
    return `${(totalLatencyMs / 1000).toFixed(totalLatencyMs >= 10000 ? 0 : 1)}s`;
  }

  return `${Math.round(totalLatencyMs)}ms`;
}

function formatMethodLabel(method: TaskAttempt["verification_method"]) {
  if (!method) {
    return "Unknown";
  }

  return method
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default function AttemptsSection({ attempts }: AttemptsSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [expandedAttempt, setExpandedAttempt] = useState<string | null>(null);

  function toggleAttempt(attemptId: string) {
    setExpandedAttempt((current) => (current === attemptId ? null : attemptId));
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[#2A2A26] bg-[#141412] shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
      <div className="flex items-center justify-between gap-4 px-5 py-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-[#F5F4F0]">Attempts</h2>
          <span className="rounded-full bg-[#23231F] px-2 py-0.5 text-xs text-[#8A8880]">
            {attempts.length}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          className="inline-flex items-center rounded-lg border border-[#2A2A26] bg-[#10100E] px-3 py-1.5 text-xs font-medium text-[#8A8880] transition-colors hover:bg-[#23231F] hover:text-[#F5F4F0]"
        >
          {expanded ? "Hide attempts" : `Show ${attempts.length} attempts`}
        </button>
      </div>

      {expanded ? (
        <div className="divide-y divide-[#2A2A26]">
          {attempts.map((attempt) => {
            const isOpen = expandedAttempt === attempt.id;

            return (
              <div key={attempt.id}>
                <button
                  type="button"
                  onClick={() => toggleAttempt(attempt.id)}
                  className="flex w-full items-center gap-3 py-3 px-5 text-left cursor-pointer hover:bg-[#10100E] transition-colors"
                >
                  <span className="font-mono text-xs bg-[#23231F] px-2 py-0.5 rounded">
                    #{attempt.attempt_index}
                  </span>
                  <span className="font-mono text-xs text-[#8A8880]">
                    {attempt.tool_name}
                  </span>
                  <StatusBadge status={attempt.outcome ?? "pending"} />
                  {attempt.final_confidence !== null ? (
                    <span className="font-mono text-sm font-semibold text-[#F5F4F0]">
                      {Math.round(attempt.final_confidence * 100)}%
                    </span>
                  ) : null}
                  <span className="text-xs text-[#6F6D66]">
                    {formatLatency(attempt.total_latency_ms)}
                  </span>
                  <span className="text-xs font-mono text-[#6F6D66]">
                    ${attempt.estimated_cost_usd.toFixed(4)}
                  </span>
                  <span className="ml-auto">
                    <svg
                      aria-hidden="true"
                      className={`h-4 w-4 text-[#6F6D66] transition-transform ${
                        isOpen ? "rotate-180" : ""
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth="1.8"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="m6 9 6 6 6-6"
                      />
                    </svg>
                  </span>
                </button>

                {isOpen ? (
                  <div className="px-5 pb-4">
                    <div className="rounded-xl bg-[#10100E] px-4 py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-[#23231F] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#8A8880]">
                          {formatMethodLabel(attempt.verification_method)}
                        </span>
                      </div>

                      <div className="mt-3">
                        <p className="text-[10px] uppercase tracking-widest text-[#6F6D66]">
                          Execution Steps
                        </p>
                        <ol className="mt-2 list-decimal pl-4 text-xs text-[#8A8880] space-y-1">
                          {attempt.execution_steps.length > 0 ? (
                            attempt.execution_steps.map((step, index) => (
                              <li key={`${attempt.id}-step-${index}`}>
                                {JSON.stringify(step)}
                              </li>
                            ))
                          ) : (
                            <li>No execution steps recorded.</li>
                          )}
                        </ol>
                      </div>

                      <div className="mt-3">
                        <p className="text-[10px] uppercase tracking-widest text-[#6F6D66]">
                          Tool Calls
                        </p>
                        <pre className="mt-2 max-h-32 overflow-auto rounded-xl bg-[#23231F] p-3 font-mono text-[11px] text-[#8A8880]">
                          {JSON.stringify(attempt.tool_calls, null, 2)}
                        </pre>
                      </div>

                      {attempt.error ? (
                        <div className="mt-2 border border-[#FCA5A5] bg-[#FEF2F2] rounded-xl px-3 py-2 text-xs text-[#991B1B]">
                          {attempt.error}
                        </div>
                      ) : null}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

