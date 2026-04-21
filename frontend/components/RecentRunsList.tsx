"use client";

import Link from "next/link";

import ConfidenceBar from "@/components/ConfidenceBar";
import StatusBadge from "@/components/StatusBadge";
import { relativeTime } from "@/lib/utils";
import type { RunSummary } from "@/types/run";

type RecentRunsListProps = {
  initialRuns: RunSummary[];
};

export default function RecentRunsList({ initialRuns }: RecentRunsListProps) {
  const runs = initialRuns.slice(0, 8);

  if (runs.length === 0) {
    return (
      <div className="mt-6 rounded-2xl border border-dashed border-[#E2DAD0] bg-[#F7F3EE] px-6 py-10 text-center text-sm text-[#9C948A]">
        No runs yet.
      </div>
    );
  }

  return (
    <div className="mt-6">
      <div className="overflow-hidden rounded-2xl border border-[#E2DAD0] bg-white">
        <table className="w-full text-sm">
          <thead className="bg-[#F7F3EE]">
            <tr className="text-[10px] uppercase tracking-widest text-[#9C948A]">
              <th className="px-4 py-3 text-left font-medium">Goal</th>
              <th className="px-4 py-3 text-left font-medium">Kind</th>
              <th className="px-4 py-3 text-left font-medium">Status</th>
              <th className="px-4 py-3 text-left font-medium">Tasks</th>
              <th className="px-4 py-3 text-left font-medium">Confidence</th>
              <th className="px-4 py-3 text-left font-medium">Created</th>
              <th className="px-4 py-3 text-left font-medium">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E2DAD0]">
            {runs.map((run) => (
              <tr key={run.id}>
                <td className="py-3.5 px-4">
                  <div className="max-w-[280px]">
                    <Link
                      href={`/runs/${run.id}`}
                      className="block truncate text-[#1A1410] font-medium hover:underline underline-offset-2"
                    >
                      {run.goal}
                    </Link>
                  </div>
                </td>
                <td className="py-3.5 px-4">
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
                <td className="py-3.5 px-4">
                  <StatusBadge status={run.status} />
                </td>
                <td className="py-3.5 px-4 font-[family-name:var(--font-geist-mono)] text-[#5C5248]">
                  {run.task_count}
                </td>
                <td className="py-3.5 px-4">
                  <ConfidenceBar value={run.latest_confidence} width={56} />
                </td>
                <td className="py-3.5 px-4 text-[#5C5248]" title={run.created_at}>
                  {relativeTime(run.created_at)}
                </td>
                <td className="py-3.5 px-4">
                  <Link
                    href={`/runs/${run.id}`}
                    className="text-[#1D4ED8] hover:underline text-xs"
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Link
        href="/runs"
        className="text-sm text-[#1D4ED8] hover:underline mt-4 block text-right"
      >
        View all runs →
      </Link>
    </div>
  );
}
