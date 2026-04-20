import Link from "next/link";

import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

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

function confidenceTone(confidence: number) {
  if (confidence >= 0.8) {
    return "bg-[#166534]";
  }

  if (confidence >= 0.5) {
    return "bg-[#B45309]";
  }

  return "bg-[#991B1B]";
}

export default async function RunsPage() {
  const runs = await api.getRuns();

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-[#1A1410]">
            Runs
          </h1>
          <p className="text-sm text-[#9C948A] mt-1">
            All verification runs, newest first.
          </p>
        </div>
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-xl bg-[#1A1410] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#2D2520]"
        >
          New Run
        </Link>
      </div>

      <div className="overflow-hidden rounded-2xl border border-[#E2DAD0] bg-white shadow-sm">
        {runs.length === 0 ? (
          <div className="py-16 text-center">
            <svg
              aria-hidden="true"
              className="mx-auto h-8 w-8 text-[#C8BEB2]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.8"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v9A2.5 2.5 0 0 1 17.5 19h-11A2.5 2.5 0 0 1 4 16.5v-9Zm1.5 0L12 12l6.5-4.5"
              />
            </svg>
            <p className="text-sm font-medium text-[#5C5248] mt-3">No runs yet</p>
            <Link
              href="/dashboard"
              className="inline-flex items-center rounded-xl bg-[#1A1410] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#2D2520] mt-5"
            >
              Start your first run →
            </Link>
          </div>
        ) : (
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
                    {run.latest_confidence === null ? (
                      <span className="text-[#9C948A]">—</span>
                    ) : (
                      <div className="flex flex-col gap-1">
                        <span className="text-[#1A1410] font-medium">
                          {Math.round(run.latest_confidence * 100)}%
                        </span>
                        <div className="h-1 w-14 rounded-full bg-[#E2DAD0]">
                          <div
                            className={`h-1 rounded-full ${confidenceTone(
                              run.latest_confidence
                            )}`}
                            style={{ width: `${Math.max(0, Math.min(100, run.latest_confidence * 100))}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </td>
                  <td
                    className="py-3.5 px-4 text-[#5C5248]"
                    title={run.created_at}
                  >
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
        )}
      </div>
    </div>
  );
}
