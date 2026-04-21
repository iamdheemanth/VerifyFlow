"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import ConfidenceBar from "@/components/ConfidenceBar";
import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { relativeTime } from "@/lib/utils";
import type { RunSummary } from "@/types/run";

type RecentRunsListProps = {
  initialRuns: RunSummary[];
  limit?: number;
  showViewAllLink?: boolean;
};

export default function RecentRunsList({
  initialRuns,
  limit,
  showViewAllLink = true,
}: RecentRunsListProps) {
  const router = useRouter();
  const [runs, setRuns] = useState(initialRuns);
  const [deletingRunId, setDeletingRunId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const visibleRuns = useMemo(
    () => (typeof limit === "number" ? runs.slice(0, limit) : runs),
    [limit, runs]
  );

  async function handleDelete(runId: string) {
    const confirmed = window.confirm(
      "Delete this run and all of its recorded tasks, attempts, and evidence?"
    );
    if (!confirmed) {
      return;
    }

    setDeletingRunId(runId);
    setError(null);

    try {
      await api.deleteRun(runId);
      setRuns((current) => current.filter((run) => run.id !== runId));
      router.refresh();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Unable to delete this run."
      );
    } finally {
      setDeletingRunId(null);
    }
  }

  if (visibleRuns.length === 0) {
    return (
      <div className="mt-6 rounded-2xl border border-dashed border-[#E2DAD0] bg-[#F7F3EE] px-6 py-10 text-center text-sm text-[#9C948A]">
        No runs yet.
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="overflow-hidden rounded-2xl border border-[#E2DAD0] bg-white">
        <table className="w-full table-fixed text-sm">
          <thead className="bg-[#F7F3EE]">
            <tr className="text-[10px] uppercase tracking-widest text-[#9C948A]">
              <th className="px-3 py-3 text-left font-medium xl:px-4">Goal</th>
              <th className="px-3 py-3 text-left font-medium xl:px-4">Kind</th>
              <th className="px-3 py-3 text-left font-medium xl:px-4">Status</th>
              <th className="px-3 py-3 text-left font-medium xl:px-4">Tasks</th>
              <th className="px-3 py-3 text-left font-medium xl:px-4">Confidence</th>
              <th className="px-3 py-3 text-left font-medium xl:px-4">Created</th>
              <th className="px-3 py-3 text-right font-medium xl:px-5">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2DAD0]">
            {visibleRuns.map((run) => (
              <tr key={run.id}>
                <td className="px-3 py-3.5 xl:px-4">
                  <div className="max-w-[220px] xl:max-w-[280px]">
                    <Link
                      href={`/runs/${run.id}`}
                      className="block truncate text-[#1A1410] font-medium hover:underline underline-offset-2"
                    >
                      {run.goal}
                    </Link>
                  </div>
                </td>
                <td className="px-3 py-3.5 xl:px-4">
                  <span
                    className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                      run.kind === "benchmark"
                        ? "bg-[#DBEAFE] text-[#1E40AF]"
                        : "bg-[#EEE9E1] text-[#5C5248]"
                    }`}
                  >
                    {run.kind === "benchmark" ? "Benchmark" : "Standard"}
                  </span>
                </td>
                <td className="px-3 py-3.5 xl:px-4">
                  <StatusBadge status={run.status} />
                </td>
                <td className="px-3 py-3.5 font-[family-name:var(--font-geist-mono)] text-[#5C5248] xl:px-4">
                  {run.task_count}
                </td>
                <td className="px-3 py-3.5 xl:px-4">
                  <ConfidenceBar value={run.latest_confidence} width={56} />
                </td>
                <td className="px-3 py-3.5 text-[#5C5248] xl:px-4" title={run.created_at}>
                  {relativeTime(run.created_at)}
                </td>
                <td className="w-[132px] px-3 py-3.5 xl:w-[150px] xl:px-5">
                  <div className="flex justify-end">
                    <div className="hidden xl:inline-flex items-center overflow-hidden rounded-full border border-[#E2DAD0] bg-[#F7F3EE] shadow-sm">
                      <Link
                        href={`/runs/${run.id}`}
                        className="inline-flex min-w-[78px] items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#1D4ED8] transition-colors hover:bg-[#EEF4FF]"
                      >
                        <span>View</span>
                        <span aria-hidden="true">→</span>
                      </Link>
                      <div className="h-4 w-px bg-[#E2DAD0]" />
                      <button
                        type="button"
                        aria-label={`Delete run ${run.goal}`}
                        disabled={deletingRunId === run.id}
                        onClick={() => void handleDelete(run.id)}
                        className="inline-flex min-w-[42px] items-center justify-center px-3 py-1.5 text-[#991B1B] transition-colors hover:bg-[#FEF2F2] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {deletingRunId === run.id ? (
                          <span className="text-[11px] font-medium">...</span>
                        ) : (
                          <svg
                            aria-hidden="true"
                            className="h-3.5 w-3.5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth="1.8"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M4 7h16m-10 4v6m4-6v6M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 1 12a1 1 0 0 0 1 .92h8a1 1 0 0 0 1-.92L19 7"
                            />
                          </svg>
                        )}
                      </button>
                    </div>

                    <div className="flex w-[108px] flex-col gap-1 xl:hidden">
                      <Link
                        href={`/runs/${run.id}`}
                        className="inline-flex items-center justify-center gap-1.5 rounded-full border border-[#D9E5FF] bg-[#EEF4FF] px-3 py-1.5 text-xs font-medium text-[#1D4ED8] transition-colors hover:bg-[#E3EDFF]"
                      >
                        <span>View</span>
                        <span aria-hidden="true">→</span>
                      </Link>
                      <button
                        type="button"
                        disabled={deletingRunId === run.id}
                        onClick={() => void handleDelete(run.id)}
                        className="inline-flex items-center justify-center gap-1.5 rounded-full border border-[#F3CACA] bg-[#FEF2F2] px-3 py-1.5 text-xs font-medium text-[#991B1B] transition-colors hover:bg-[#FDE6E6] disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {deletingRunId === run.id ? (
                          <span>Deleting...</span>
                        ) : (
                          <>
                            <svg
                              aria-hidden="true"
                              className="h-3.5 w-3.5"
                              fill="none"
                              viewBox="0 0 24 24"
                              stroke="currentColor"
                              strokeWidth="1.8"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                d="M4 7h16m-10 4v6m4-6v6M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m-8 0 1 12a1 1 0 0 0 1 .92h8a1 1 0 0 0 1-.92L19 7"
                              />
                            </svg>
                            <span>Delete</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {error ? <p className="mt-3 text-sm text-[#991B1B]">{error}</p> : null}

      {showViewAllLink ? (
        <Link
          href="/runs"
          className="text-sm text-[#1D4ED8] hover:underline mt-4 block text-right"
        >
          View all runs →
        </Link>
      ) : null}
    </div>
  );
}
