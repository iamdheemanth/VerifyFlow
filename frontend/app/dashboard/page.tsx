import Link from "next/link";

import DemoSeedButton from "@/components/DemoSeedButton";
import RecentRunsList from "@/components/RecentRunsList";
import RunForm from "@/components/RunForm";
import { serverApi } from "@/lib/server-api";
import type { ReliabilityOverview, RunSummary } from "@/types/run";

export const dynamic = "force-dynamic";

function StatPill({
  value,
  label,
}: {
  value: string | number;
  label: string;
}) {
  return (
    <div className="inline-flex items-center gap-1.5 bg-[#23231F] rounded-full px-3 py-1 text-sm text-[#8A8880]">
      <span className="font-semibold text-[#F5F4F0]">{value}</span>
      <span>{label}</span>
    </div>
  );
}

export default async function DashboardPage() {
  let runs: RunSummary[] = [];
  let overview: ReliabilityOverview | null = null;

  try {
    [runs, overview] = await Promise.all([serverApi.getRuns(), serverApi.getOverview()]);
  } catch {
    runs = [];
    overview = null;
  }

  const stats = [
    { value: overview?.total_runs ?? 0, label: "Runs" },
    { value: overview?.completed_runs ?? 0, label: "Completed" },
    { value: overview?.failed_runs ?? 0, label: "Failed" },
    {
      value: overview ? `${Math.round(overview.average_confidence * 100)}%` : "0%",
      label: "Avg Confidence",
    },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-8 px-6 py-8 md:px-10">
      <section className="border-b border-[#2A2A26] pb-10">
        <div className="grid gap-10 lg:grid-cols-[minmax(0,0.9fr)_minmax(420px,0.8fr)] lg:items-start">
          <div>
          <p className="text-sm uppercase tracking-[0.3em] text-[#6F6D66]">
            VERIFYFLOW
          </p>
          <h1 className="mt-4 max-w-xl text-5xl font-semibold tracking-tight text-[#F5F4F0] md:text-6xl">
            Launch a <span className="text-[#C8A882]">verification</span> run.
          </h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-[#8A8880]">
            VerifyFlow turns ambitious AI tasks into structured runs with
            traceable execution and reviewable evidence. Start with a goal,
            define success, and monitor how each claim holds up under
            verification.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            {stats.map((stat) => (
              <StatPill key={stat.label} value={stat.value} label={stat.label} />
            ))}
          </div>
        </div>

          <div className="lg:border-l lg:border-[#2A2A26] lg:pl-10">
            <div className="mb-6">
              <div>
                <h2 className="text-xl font-semibold text-[#F5F4F0]">New Run</h2>
                <p className="mt-1 max-w-md text-sm leading-6 text-[#8A8880]">
                  Define the objective, add optional acceptance criteria, and launch a fresh verification workflow.
                </p>
              </div>
            </div>
            <RunForm />
          </div>
        </div>
      </section>

      <section className="border-t border-[#2A2A26] pt-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight text-[#F5F4F0]">
            Recent Runs
          </h2>
          <div className="flex items-center gap-3">
            <div className="inline-flex items-center rounded-full bg-[#23231F] px-3 py-1 text-sm text-[#8A8880]">
              <span className="font-semibold text-[#F5F4F0] mr-1">{runs.length}</span>
              total
            </div>
            <DemoSeedButton />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/review"
            className="inline-flex items-center rounded-full border border-[#2A2A26] bg-[#10100E] px-4 py-2 text-sm text-[#8A8880] transition-colors hover:bg-[#23231F] hover:text-[#F5F4F0]"
          >
            Review Queue
          </Link>
          <Link
            href="/benchmarks"
            className="inline-flex items-center rounded-full border border-[#2A2A26] bg-[#10100E] px-4 py-2 text-sm text-[#8A8880] transition-colors hover:bg-[#23231F] hover:text-[#F5F4F0]"
          >
            Benchmarks
          </Link>
          <Link
            href="/configs"
            className="inline-flex items-center rounded-full border border-[#2A2A26] bg-[#10100E] px-4 py-2 text-sm text-[#8A8880] transition-colors hover:bg-[#23231F] hover:text-[#F5F4F0]"
          >
            Config Comparison
          </Link>
        </div>

        <div className="mt-6">
          <RecentRunsList initialRuns={runs} limit={8} />
        </div>
      </section>
    </div>
  );
}

