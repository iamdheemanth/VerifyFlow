import Link from "next/link";

import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { Run } from "@/types/run";

export const dynamic = "force-dynamic";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function SkeletonCard({
  title,
  lines = 3,
}: {
  title: string;
  lines?: number;
}) {
  return (
    <div className="rounded-2xl border border-[#E2DAD0] bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#1A1410]">{title}</h2>
        <div className="skeleton h-4 w-16" />
      </div>
      <div className="mt-4 space-y-3">
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={`${title}-${index}`}
            className={`skeleton h-4 ${index === lines - 1 ? "w-2/3" : "w-full"}`}
          />
        ))}
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-full max-w-md rounded-2xl border border-[#E2DAD0] bg-white p-8 text-center shadow-sm">
          <svg
            aria-hidden="true"
            className="mx-auto h-10 w-10 text-[#C8BEB2]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"
            />
          </svg>
          <h1 className="mt-4 text-xl font-semibold text-[#1A1410]">
            Run not found
          </h1>
          <p className="mt-2 text-sm text-[#5C5248]">
            The run you requested could not be loaded.
          </p>
          <Link
            href="/runs"
            className="mt-6 inline-flex items-center rounded-xl bg-[#1A1410] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#2D2520]"
          >
            Back to runs
          </Link>
        </div>
      </div>
    </div>
  );
}

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let run: Run;

  try {
    run = await api.getRun(id);
  } catch {
    return <ErrorState />;
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10 space-y-6 page-enter">
      <section className="bg-white border border-[#E2DAD0] rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center min-w-0">
              <Link
                href="/runs"
                className="text-[#9C948A] hover:text-[#5C5248] text-sm"
              >
                Runs
              </Link>
              <span className="text-[#C8BEB2] mx-1">/</span>
              <span className="text-[#5C5248] text-sm truncate max-w-md">
                {run.goal}
              </span>
            </div>

            <h1 className="text-2xl font-semibold text-[#1A1410] mt-2 leading-tight">
              {run.goal}
            </h1>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <StatusBadge status={run.status} />
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                  run.kind === "benchmark"
                    ? "bg-[#DBEAFE] text-[#1E40AF]"
                    : "bg-[#EEE9E1] text-[#5C5248]"
                }`}
              >
                {run.kind === "benchmark" ? "Benchmark" : "Standard"}
              </span>
              <span className="font-[family-name:var(--font-geist-mono)] text-[10px] text-[#9C948A] bg-[#EEE9E1] px-2 py-1 rounded-lg">
                {run.id}
              </span>
            </div>
          </div>

          <div className="text-xs text-[#9C948A] lg:text-right shrink-0">
            <p>Created {formatDate(run.created_at)}</p>
            <p className="mt-1">Updated {formatDate(run.updated_at)}</p>
          </div>
        </div>

        {run.acceptance_criteria ? (
          <div className="bg-[#EEE9E1] rounded-xl px-4 py-3 mt-4">
            <p className="text-[10px] uppercase tracking-widest text-[#9C948A]">
              Acceptance Criteria
            </p>
            <p className="text-sm text-[#5C5248] italic mt-1">
              {run.acceptance_criteria}
            </p>
          </div>
        ) : null}
      </section>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-6">
          <SkeletonCard title="Tasks Section" lines={4} />
          <SkeletonCard title="Attempts Section" lines={5} />
          <SkeletonCard title="Ledger Section" lines={4} />
        </div>

        <div className="space-y-6">
          <SkeletonCard title="Telemetry Card" lines={3} />
          <SkeletonCard title="Escalations Card" lines={4} />
          <SkeletonCard title="Config Card" lines={3} />
        </div>
      </div>
    </div>
  );
}
