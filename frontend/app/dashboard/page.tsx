import Link from "next/link";

import DemoSeedButton from "@/components/DemoSeedButton";
import RecentRunsList from "@/components/RecentRunsList";
import RunForm from "@/components/RunForm";
import { api } from "@/lib/api";
import type { ReliabilityOverview, RunSummary } from "@/types/run";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  let runs: RunSummary[] = [];
  let overview: ReliabilityOverview | null = null;
  try {
    [runs, overview] = await Promise.all([api.getRuns(), api.getOverview()]);
  } catch {
    runs = [];
    overview = null;
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
            <div className="flex items-center gap-3">
              <div className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                {runs.length} total
              </div>
              <DemoSeedButton />
            </div>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Runs</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{overview?.total_runs ?? 0}</p>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Completed</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-700">{overview?.completed_runs ?? 0}</p>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Failed</p>
              <p className="mt-2 text-2xl font-semibold text-rose-700">{overview?.failed_runs ?? 0}</p>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Escalated</p>
              <p className="mt-2 text-2xl font-semibold text-amber-700">{overview?.escalated_runs ?? 0}</p>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Avg confidence</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">
                {overview ? `${Math.round(overview.average_confidence * 100)}%` : "—"}
              </p>
            </div>
            <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Token volume</p>
              <p className="mt-2 text-2xl font-semibold text-slate-950">{overview?.total_tokens ?? 0}</p>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/review" className="rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800">
              Review Queue
            </Link>
            <Link href="/benchmarks" className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
              Benchmarks
            </Link>
            <Link href="/configs" className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
              Config Comparison
            </Link>
          </div>

          <RecentRunsList initialRuns={runs} />
        </section>
      </div>
    </main>
  );
}
