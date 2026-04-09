"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

import LedgerTable from "@/components/LedgerTable";
import TaskCard from "@/components/TaskCard";
import { api } from "@/lib/api";
import type { LedgerEntry, Run, RunStreamEvent } from "@/types/run";

function statusTone(status: string) {
  if (status === "verified" || status === "completed") return "bg-emerald-100 text-emerald-800";
  if (status === "claimed" || status === "executing" || status === "planning") return "bg-amber-100 text-amber-800";
  if (status === "failed" || status === "escalated") return "bg-rose-100 text-rose-800";
  return "bg-slate-200 text-slate-700";
}

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const runId = params.id;
  const [run, setRun] = useState<Run | null>(null);
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [streamState, setStreamState] = useState("connecting");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [runData, ledgerData] = await Promise.all([api.getRun(runId), api.getLedger(runId)]);
        if (!cancelled) {
          setRun(runData);
          setLedgerEntries(ledgerData);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load run.");
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    if (!runId) return;

    const cleanup = api.streamRun(runId, async (event: RunStreamEvent) => {
      if (event.type === "error") {
        setStreamState("disconnected");
        return;
      }

      setStreamState(event.type === "run_complete" ? "complete" : "live");

      if (event.type === "task_update") {
        setRun((current) =>
          current
            ? {
                ...current,
                tasks: current.tasks.map((task) =>
                  task.id === event.task_id ? { ...task, status: event.status } : task
                ),
              }
            : current
        );
      }

      try {
        const [runData, ledgerData] = await Promise.all([api.getRun(runId), api.getLedger(runId)]);
        setRun(runData);
        setLedgerEntries(ledgerData);
      } catch {
        setStreamState("disconnected");
      }
    });

    return cleanup;
  }, [runId]);

  const orderedTasks = useMemo(
    () => (run ? [...run.tasks].sort((a, b) => a.index - b.index) : []),
    [run]
  );

  if (error) {
    return <div className="min-h-screen bg-stone-100 px-6 py-10 text-rose-700">{error}</div>;
  }

  if (!run) {
    return <div className="min-h-screen bg-stone-100 px-6 py-10 text-slate-500">Loading run...</div>;
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f6f1e6_0%,#efe9de_100%)] px-6 py-10 text-slate-900 md:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Link href="/dashboard" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          ← Back to dashboard
        </Link>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-4xl">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{run.id}</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{run.goal}</h1>
              {run.acceptance_criteria ? (
                <p className="mt-4 max-w-3xl text-sm leading-6 text-slate-600">{run.acceptance_criteria}</p>
              ) : null}
            </div>
            <div className="flex flex-col items-end gap-2">
              <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusTone(run.status)}`}>
                {run.status}
              </span>
              <span className="text-xs uppercase tracking-[0.2em] text-slate-400">stream: {streamState}</span>
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-slate-950">Tasks</h2>
              <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                {orderedTasks.length} total
              </span>
            </div>
            <div className="mt-5 grid gap-4">
              {orderedTasks.map((task) => (
                <TaskCard key={task.id} task={task} ledgerEntries={ledgerEntries} />
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-slate-950">Verification Ledger</h2>
              <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                {ledgerEntries.length} events
              </span>
            </div>
            <div className="mt-5">
              <LedgerTable entries={ledgerEntries} />
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
