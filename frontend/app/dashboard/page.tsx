import Link from "next/link";

import DemoSeedButton from "@/components/DemoSeedButton";
import RecentRunsList from "@/components/RecentRunsList";
import RunForm from "@/components/RunForm";
import { api } from "@/lib/api";
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
    <div className="inline-flex items-center gap-1.5 bg-[#EEE9E1] rounded-full px-3 py-1 text-sm text-[#5C5248]">
      <span className="font-semibold text-[#1A1410]">{value}</span>
      <span>{label}</span>
    </div>
  );
}

export default async function DashboardPage() {
  let runs: RunSummary[] = [];
  let overview: ReliabilityOverview | null = null;

  try {
    [runs, overview] = await Promise.all([api.getRuns(), api.getOverview()]);
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
    <div className="space-y-6 max-w-7xl mx-auto px-6 py-8 md:px-10">
      <section className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <div className="bg-white border border-[#E2DAD0] rounded-2xl p-8 shadow-sm">
          <p className="text-xs uppercase tracking-[0.3em] text-[#9C948A]">
            VERIFYFLOW
          </p>
          <h1 className="text-4xl font-semibold tracking-tight text-[#1A1410] mt-3 max-w-sm">
            Launch a verification run.
          </h1>
          <p className="text-sm leading-6 text-[#5C5248] mt-3 max-w-xl">
            VerifyFlow turns ambitious AI tasks into structured runs with
            traceable execution and reviewable evidence. Start with a goal,
            define success, and monitor how each claim holds up under
            verification.
          </p>
          <div className="flex flex-wrap gap-2 mt-6">
            {stats.map((stat) => (
              <StatPill key={stat.label} value={stat.value} label={stat.label} />
            ))}
          </div>
        </div>

        <div className="bg-[#1A1410] rounded-2xl p-8">
          <h2 className="text-xl font-semibold text-white">New Run</h2>
          <p className="text-sm text-[#9C8C80] mt-1 mb-6">
            Define the objective, add optional acceptance criteria, and launch a
            fresh verification workflow.
          </p>
          <RunForm />
        </div>
      </section>

      <section className="bg-white border border-[#E2DAD0] rounded-2xl p-8 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <h2 className="text-2xl font-semibold tracking-tight text-[#1A1410]">
            Recent Runs
          </h2>
          <div className="flex items-center gap-3">
            <div className="inline-flex items-center rounded-full bg-[#EEE9E1] px-3 py-1 text-sm text-[#5C5248]">
              <span className="font-semibold text-[#1A1410] mr-1">{runs.length}</span>
              total
            </div>
            <DemoSeedButton />
          </div>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/review"
            className="inline-flex items-center rounded-full border border-[#E2DAD0] bg-[#F7F3EE] px-4 py-2 text-sm text-[#5C5248] transition-colors hover:bg-[#EEE9E1] hover:text-[#1A1410]"
          >
            Review Queue
          </Link>
          <Link
            href="/benchmarks"
            className="inline-flex items-center rounded-full border border-[#E2DAD0] bg-[#F7F3EE] px-4 py-2 text-sm text-[#5C5248] transition-colors hover:bg-[#EEE9E1] hover:text-[#1A1410]"
          >
            Benchmarks
          </Link>
          <Link
            href="/configs"
            className="inline-flex items-center rounded-full border border-[#E2DAD0] bg-[#F7F3EE] px-4 py-2 text-sm text-[#5C5248] transition-colors hover:bg-[#EEE9E1] hover:text-[#1A1410]"
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
