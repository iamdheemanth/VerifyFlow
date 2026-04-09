import Link from "next/link";

import RunForm from "@/components/RunForm";
import { api } from "@/lib/api";
import type { RunSummary } from "@/types/run";

export const dynamic = "force-dynamic";

function truncateGoal(goal: string) {
  return goal.length > 60 ? `${goal.slice(0, 57)}...` : goal;
}

function statusClasses(status: string) {
  if (status === "completed") return "bg-emerald-100 text-emerald-800";
  if (status === "executing" || status === "planning") return "bg-amber-100 text-amber-800";
  if (status === "failed" || status === "escalated") return "bg-rose-100 text-rose-800";
  return "bg-slate-200 text-slate-700";
}

export default async function DashboardPage() {
  let runs: RunSummary[] = [];
  try {
    runs = await api.getRuns();
  } catch {
    runs = [];
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f8efe4,transparent_40%),linear-gradient(180deg,#fcfaf6_0%,#f2ede2_100%)] px-6 py-10 text-slate-900 md:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <section className="grid gap-6 lg:grid-cols-[1.3fr_0.9fr]">
          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.4)] backdrop-blur">
            <p className="text-sm uppercase tracking-[0.3em] text-amber-700">VerifyFlow</p>
            <h1 className="mt-3 max-w-2xl font-[family-name:var(--font-geist-sans)] text-4xl font-semibold tracking-tight text-slate-950 md:text-5xl">
              Launch a verification run and watch claims turn into evidence.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
              Create a run, track task execution in real time, and inspect the ledger that records what was claimed, what was verified, and what was escalated.
            </p>
          </div>
          <div className="rounded-[2rem] border border-slate-200/80 bg-[#13212e] p-8 text-white shadow-[0_30px_80px_-40px_rgba(15,23,42,0.6)]">
            <h2 className="text-xl font-semibold">New Run</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Describe the goal, add acceptance criteria if you have them, and VerifyFlow will break the work into verifiable steps.
            </p>
            <div className="mt-6">
              <RunForm />
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-slate-950">Recent Runs</h2>
              <p className="mt-1 text-sm text-slate-500">Newest first, with quick status and task counts.</p>
            </div>
            <div className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
              {runs.length} total
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            {runs.map((run) => (
              <Link
                key={run.id}
                href={`/runs/${run.id}`}
                className="group rounded-[1.5rem] border border-slate-200 bg-white p-5 transition hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-lg"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{run.id}</p>
                    <h3 className="mt-2 text-lg font-semibold text-slate-900 group-hover:text-slate-950">
                      {truncateGoal(run.goal)}
                    </h3>
                  </div>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusClasses(run.status)}`}>
                    {run.status}
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-500">
                  <span>Created {new Date(run.created_at).toLocaleString()}</span>
                  <span>{run.task_count} tasks</span>
                </div>
              </Link>
            ))}

            {runs.length === 0 ? (
              <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-slate-500">
                No runs yet. Create the first one above.
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
