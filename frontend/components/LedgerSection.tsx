"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";
import type { LedgerEntry } from "@/types/run";

type LedgerSectionProps = {
  runId: string;
};

function relativeTime(createdAt: string) {
  const seconds = Math.max(
    0,
    Math.floor((Date.now() - new Date(createdAt).getTime()) / 1000)
  );

  if (seconds < 60) {
    return "just now";
  }

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }

  const days = Math.floor(hours / 24);
  return `${days} days ago`;
}

function truncate(value: string, max: number) {
  return value.length > max ? `${value.slice(0, max - 3)}...` : value;
}

function methodClasses(method: LedgerEntry["verification_method"]) {
  if (method === "llm_judge") {
    return "bg-[#EDE9FE] text-[#4C1D95]";
  }

  if (method === "hybrid") {
    return "bg-[#CCFBF1] text-[#0F766E]";
  }

  return "bg-[#23231F] text-[#8A8880]";
}

function methodLabel(method: LedgerEntry["verification_method"]) {
  return method
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function confidenceTone(confidence: number) {
  if (confidence >= 0.8) {
    return "bg-[#166534]";
  }

  if (confidence >= 0.5) {
    return "bg-[#B45309]";
  }

  return "bg-[#991B1B]";
}

export default function LedgerSection({ runId }: LedgerSectionProps) {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadEntries() {
      setLoading(true);
      setError(null);

      try {
        const result = await api.getLedger(runId);
        if (!cancelled) {
          setEntries(result);
        }
      } catch (loadError) {
        if (!cancelled) {
          setEntries([]);
          setError(getApiErrorMessage(loadError, "Unable to load ledger entries."));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadEntries();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  return (
    <section className="overflow-hidden rounded-2xl border border-[#2A2A26] bg-[#141412] shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
      <div className="px-5 py-4">
        <h2 className="text-sm font-semibold text-[#F5F4F0]">
          Verification Ledger
        </h2>
        <p className="text-xs text-[#6F6D66] mt-0.5">
          Immutable record of all verification decisions.
        </p>
      </div>

      {loading ? (
        <div className="px-5 pb-5 space-y-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="flex items-center gap-4">
              <div className="skeleton h-3 w-40" />
              <div className="skeleton h-3 w-16" />
              <div className="skeleton h-3 w-24" />
            </div>
          ))}
        </div>
      ) : error ? (
        <div className="px-5 pb-5">
          <p className="text-xs text-[#6F6D66]">{error}</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="px-5 pb-8 pt-2 text-center">
          <svg
            aria-hidden="true"
            className="mx-auto h-6 w-6 text-[#6F6D66]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 12h6m-6 4h6M8 4h8a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"
            />
          </svg>
          <p className="mt-3 text-sm text-[#8A8880]">No ledger entries yet</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-[#10100E] text-[#6F6D66]">
              <tr>
                <th className="px-5 py-3 text-left font-medium">Task</th>
                <th className="px-4 py-3 text-left font-medium">Method</th>
                <th className="px-4 py-3 text-left font-medium">Confidence</th>
                <th className="px-4 py-3 text-center font-medium">Verified</th>
                <th className="px-4 py-3 text-left font-medium">Evidence</th>
                <th className="px-4 py-3 text-left font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#2A2A26]">
              {entries.map((entry) => (
                <tr key={entry.id}>
                  <td
                    className="px-5 py-3.5 text-[#F5F4F0]"
                    title={entry.task_description}
                  >
                    {truncate(entry.task_description, 50)}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-medium ${methodClasses(
                          entry.verification_method
                        )}`}
                      >
                        {methodLabel(entry.verification_method)}
                      </span>
                      {entry.judge_reasoning ? (
                        <span
                          title={entry.judge_reasoning}
                          className="text-[#6F6D66]"
                        >
                          ⓘ
                        </span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex flex-col gap-1">
                      <span className="font-medium text-[#F5F4F0]">
                        {Math.round(entry.confidence * 100)}%
                      </span>
                      <div className="h-1 w-12 rounded-full bg-[#E2DAD0]">
                        <div
                          className={`h-1 rounded-full ${confidenceTone(
                            entry.confidence
                          )}`}
                          style={{
                            width: `${Math.max(
                              0,
                              Math.min(100, entry.confidence * 100)
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    <span
                      className={
                        entry.verified
                          ? "font-bold text-[#166534]"
                          : "font-bold text-[#991B1B]"
                      }
                    >
                      {entry.verified ? "✓" : "✗"}
                    </span>
                  </td>
                  <td
                    className="px-4 py-3.5 text-[#8A8880]"
                    title={entry.evidence}
                  >
                    {truncate(entry.evidence, 80)}
                  </td>
                  <td className="px-4 py-3.5 text-[#6F6D66]">
                    {relativeTime(entry.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

