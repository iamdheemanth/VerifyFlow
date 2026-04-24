import Link from "next/link";

import AttemptsSection from "@/components/AttemptsSection";
import EscalationsCard from "@/components/EscalationsCard";
import LedgerSection from "@/components/LedgerSection";
import StatusBadge from "@/components/StatusBadge";
import TasksSection from "@/components/TasksSection";
import TelemetryCard from "@/components/TelemetryCard";
import { serverApi } from "@/lib/server-api";
import type { Run } from "@/types/run";

export const dynamic = "force-dynamic";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function ErrorState() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="w-full max-w-md rounded-2xl border border-[#2A2A26] bg-[#141412] p-8 text-center shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
          <svg
            aria-hidden="true"
            className="mx-auto h-10 w-10 text-[#6F6D66]"
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
          <h1 className="mt-4 text-xl font-semibold text-[#F5F4F0]">
            Run not found
          </h1>
          <p className="mt-2 text-sm text-[#8A8880]">
            The run you requested could not be loaded.
          </p>
          <Link
            href="/runs"
            className="mt-6 inline-flex items-center rounded-xl bg-[#C8A882] px-4 py-2.5 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592]"
          >
            Back to runs
          </Link>
        </div>
      </div>
    </div>
  );
}

function ConfigCard({ run }: { run: Run }) {
  const executorLabel = run.executor_config
    ? `${run.executor_config.name} · ${run.executor_config.model_name}`
    : "Default executor configuration";
  const judgeLabel = run.judge_config
    ? `${run.judge_config.name} · ${run.judge_config.model_name}`
    : "Default judge configuration";
  const benchmarkLabel = run.benchmark_case
    ? `${run.benchmark_suite?.name ?? "Benchmark suite"} · ${run.benchmark_case.name}`
    : "Standard run";

  return (
    <section className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
      <h2 className="text-sm font-semibold text-[#F5F4F0]">Configuration</h2>
      <div className="mt-4 space-y-3">
        <div className="rounded-xl bg-[#10100E] p-3">
          <p className="text-[10px] uppercase tracking-widest text-[#6F6D66]">
            Executor
          </p>
          <p className="mt-1 break-words text-sm text-[#F5F4F0]">{executorLabel}</p>
        </div>
        <div className="rounded-xl bg-[#10100E] p-3">
          <p className="text-[10px] uppercase tracking-widest text-[#6F6D66]">
            Judge
          </p>
          <p className="mt-1 break-words text-sm text-[#F5F4F0]">{judgeLabel}</p>
        </div>
        <div className="rounded-xl bg-[#10100E] p-3">
          <p className="text-[10px] uppercase tracking-widest text-[#6F6D66]">
            Run Type
          </p>
          <p className="mt-1 break-words text-sm text-[#F5F4F0]">{benchmarkLabel}</p>
        </div>
      </div>
    </section>
  );
}

function FailureRecordCard({ failureRecord }: { failureRecord: Record<string, unknown> }) {
  const message =
    typeof failureRecord.message === "string"
      ? failureRecord.message
      : "A run-level orchestration failure was recorded.";
  const category =
    typeof failureRecord.category === "string" ? failureRecord.category : null;
  const stage = typeof failureRecord.stage === "string" ? failureRecord.stage : null;

  return (
    <section className="rounded-2xl border border-[#FCA5A5] bg-[#FEF2F2] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
      <h2 className="text-sm font-semibold text-[#7F1D1D]">Failure Record</h2>
      <p className="mt-2 text-sm text-[#991B1B]">{message}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {category ? (
          <span className="rounded-full bg-[#141412] px-2.5 py-1 text-[10px] font-medium text-[#991B1B]">
            {category}
          </span>
        ) : null}
        {stage ? (
          <span className="rounded-full bg-[#141412] px-2.5 py-1 text-[10px] font-medium text-[#991B1B]">
            Stage: {stage}
          </span>
        ) : null}
      </div>
    </section>
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
    run = await serverApi.getRun(id);
  } catch {
    return <ErrorState />;
  }

  return (
    <div className="mx-auto max-w-[1400px] space-y-6 px-4 py-6 sm:px-6 md:py-8 xl:px-8 page-enter">
      <section className="bg-[#141412] border border-[#2A2A26] rounded-2xl p-6 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center min-w-0">
              <Link
                href="/runs"
                className="text-[#6F6D66] hover:text-[#8A8880] text-sm"
              >
                Runs
              </Link>
              <span className="text-[#6F6D66] mx-1">/</span>
              <span className="max-w-full truncate text-sm text-[#8A8880] lg:max-w-md">
                {run.goal}
              </span>
            </div>

            <h1 className="mt-2 break-words text-2xl font-semibold leading-tight text-[#F5F4F0] xl:text-[2rem]">
              {run.goal}
            </h1>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <StatusBadge status={run.status} />
              <span
                className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                  run.kind === "benchmark"
                    ? "bg-[#DBEAFE] text-[#1E40AF]"
                    : "bg-[#23231F] text-[#8A8880]"
                }`}
              >
                {run.kind === "benchmark" ? "Benchmark" : "Standard"}
              </span>
              <span className="max-w-full break-all font-[family-name:var(--font-geist-mono)] text-[10px] text-[#6F6D66] bg-[#23231F] px-2 py-1 rounded-lg">
                {run.id}
              </span>
            </div>
          </div>

          <div className="text-xs text-[#6F6D66] lg:text-right shrink-0">
            <p>Created {formatDate(run.created_at)}</p>
            <p className="mt-1">Updated {formatDate(run.updated_at)}</p>
          </div>
        </div>

        {run.acceptance_criteria ? (
          <div className="bg-[#23231F] rounded-xl px-4 py-3 mt-4">
            <p className="text-[10px] uppercase tracking-widest text-[#6F6D66]">
              Acceptance Criteria
            </p>
            <p className="mt-1 break-words text-sm italic text-[#8A8880]">
              {run.acceptance_criteria}
            </p>
          </div>
        ) : null}
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.9fr)_minmax(320px,0.95fr)]">
        <div className="min-w-0 space-y-6">
          <TasksSection run={run} />
          <AttemptsSection attempts={run.task_attempts} />
          <LedgerSection runId={run.id} />
        </div>

        <div className="min-w-0 space-y-6">
          <TelemetryCard telemetry={run.telemetry} />
          <EscalationsCard escalations={run.escalations} />
          <ConfigCard run={run} />
          {run.failure_record ? <FailureRecordCard failureRecord={run.failure_record} /> : null}
        </div>
      </div>
    </div>
  );
}

