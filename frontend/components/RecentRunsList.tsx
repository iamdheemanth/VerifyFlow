"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { api } from "@/lib/api";
import type { RunSummary } from "@/types/run";

type RecentRunsListProps = {
  initialRuns: RunSummary[];
};

function truncateGoal(goal: string) {
  return goal.length > 60 ? `${goal.slice(0, 57)}...` : goal;
}

function statusClasses(status: string) {
  if (status === "completed") return "bg-emerald-100 text-emerald-800";
  if (status === "executing" || status === "planning") return "bg-amber-100 text-amber-800";
  if (status === "failed" || status === "escalated") return "bg-rose-100 text-rose-800";
  return "bg-slate-200 text-slate-700";
}

export default function RecentRunsList({ initialRuns }: RecentRunsListProps) {
  const router = useRouter();
  const [runs, setRuns] = useState(initialRuns);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function handleDelete(runId: string) {
    startTransition(async () => {
      setError(null);
      try {
        await api.deleteRun(runId);
        setRuns((current) => current.filter((run) => run.id !== runId));
        router.refresh();
      } catch (deleteError) {
        setError(deleteError instanceof Error ? deleteError.message : "Failed to delete run.");
      }
    });
  }

  return (
    <div className="mt-6 grid gap-4">
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}

      {runs.map((run) => (
        <div
          key={run.id}
          className="rounded-[1.5rem] border border-slate-200 bg-white p-5 transition hover:border-slate-300 hover:shadow-lg"
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <Link href={`/runs/${run.id}`} className="group min-w-0 flex-1">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{run.id}</p>
              <h3 className="mt-2 text-lg font-semibold text-slate-900 group-hover:text-slate-950">
                {truncateGoal(run.goal)}
              </h3>
            </Link>
            <div className="flex items-center gap-3">
              <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusClasses(run.status)}`}>
                {run.status}
              </span>
              <button
                type="button"
                disabled={isPending}
                onClick={() => handleDelete(run.id)}
                className="rounded-full border border-rose-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Delete
              </button>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-500">
            <span>Created {new Date(run.created_at).toLocaleString()}</span>
            <span className="capitalize">{run.kind}</span>
            <span>{run.task_count} tasks</span>
            <span>
              Confidence {run.latest_confidence !== null ? `${Math.round(run.latest_confidence * 100)}%` : "—"}
            </span>
          </div>
        </div>
      ))}

      {runs.length === 0 ? (
        <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
          No runs yet. Create the first one above.
        </div>
      ) : null}
    </div>
  );
}
