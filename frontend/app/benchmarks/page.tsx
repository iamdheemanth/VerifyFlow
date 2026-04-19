import Link from "next/link";

import { api } from "@/lib/api";
import type { BenchmarkCase, BenchmarkOverview, BenchmarkSuite } from "@/types/run";

export const dynamic = "force-dynamic";

export default async function BenchmarksPage() {
  let overview: BenchmarkOverview[] = [];
  let suites: BenchmarkSuite[] = [];
  let cases: BenchmarkCase[] = [];

  try {
    [overview, suites, cases] = await Promise.all([
      api.getBenchmarkOverview(),
      api.getBenchmarkSuites(),
      api.getBenchmarkCases(),
    ]);
  } catch {
    overview = [];
    suites = [];
    cases = [];
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#f8efe4,transparent_40%),linear-gradient(180deg,#fcfaf6_0%,#f2ede2_100%)] px-6 py-10 text-slate-900 md:px-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Link href="/dashboard" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          ← Back to dashboard
        </Link>

        <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-8 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
          <p className="text-sm uppercase tracking-[0.3em] text-amber-700">Experimentation</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">
            Benchmark the verifier, not just the model.
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            These suites measure claim accuracy, verification pass rate, retry behavior, escalation rate, and error patterns across labelled reliability tasks.
          </p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-slate-950">Benchmark Overview</h2>
              <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                {overview.length} suites
              </span>
            </div>
            <div className="mt-5 grid gap-4">
              {overview.map((item) => (
                <article key={item.suite_name} className="rounded-[1.5rem] border border-slate-200 bg-slate-50 p-5">
                  <h3 className="text-lg font-semibold text-slate-950">{item.suite_name}</h3>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    <Metric label="Runs" value={item.run_count.toString()} />
                    <Metric label="Claim accuracy" value={percent(item.claim_accuracy)} />
                    <Metric label="Verification pass rate" value={percent(item.verification_pass_rate)} />
                    <Metric label="Retry rate" value={percent(item.retry_rate)} />
                    <Metric label="Escalation rate" value={percent(item.escalation_rate)} />
                    <Metric label="Avg confidence" value={percent(item.average_confidence)} />
                    <Metric label="False positives" value={percent(item.false_positive_rate)} />
                    <Metric label="False negatives" value={percent(item.false_negative_rate)} />
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="grid gap-6">
            <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold text-slate-950">Suites</h2>
                <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                  {suites.length}
                </span>
              </div>
              <div className="mt-5 grid gap-3">
                {suites.map((suite) => (
                  <article key={suite.id} className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                    <h3 className="text-base font-semibold text-slate-950">{suite.name}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{suite.description || "No description yet."}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-[2rem] border border-slate-200/80 bg-white/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold text-slate-950">Benchmark Cases</h2>
                <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-600">
                  {cases.length}
                </span>
              </div>
              <div className="mt-5 grid gap-3">
                {cases.map((benchmarkCase) => (
                  <article key={benchmarkCase.id} className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
                    <h3 className="text-base font-semibold text-slate-950">{benchmarkCase.name}</h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{benchmarkCase.goal}</p>
                    {benchmarkCase.acceptance_criteria ? (
                      <p className="mt-2 text-sm leading-6 text-slate-500">{benchmarkCase.acceptance_criteria}</p>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}
