import Link from "next/link";

import { serverApi } from "@/lib/server-api";
import type { BenchmarkOverview } from "@/types/run";

export const dynamic = "force-dynamic";

function rateColor(value: number, inverse = false) {
  if (inverse) {
    if (value <= 0.1) {
      return "text-[#166534]";
    }

    if (value <= 0.25) {
      return "text-[#B45309]";
    }

    return "text-[#991B1B]";
  }

  if (value >= 0.8) {
    return "text-[#166534]";
  }

  if (value >= 0.6) {
    return "text-[#B45309]";
  }

  return "text-[#991B1B]";
}

function rateBarColor(value: number) {
  if (value >= 0.8) {
    return "bg-[#166534]";
  }

  if (value >= 0.6) {
    return "bg-[#B45309]";
  }

  return "bg-[#991B1B]";
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function MetricCell({
  label,
  value,
  valueClassName,
  barValue,
}: {
  label: string;
  value: string;
  valueClassName: string;
  barValue?: number;
}) {
  return (
    <div className="bg-[#F7F3EE] rounded-xl p-3">
      <span className="text-[9px] uppercase tracking-widest text-[#9C948A]">
        {label}
      </span>
      <span className={`block text-lg font-semibold font-mono mt-0.5 ${valueClassName}`}>
        {value}
      </span>
      {typeof barValue === "number" ? (
        <div className="mt-2 h-1 w-12 rounded-full bg-[#E2DAD0]">
          <div
            className={`h-1 rounded-full ${rateBarColor(barValue)}`}
            style={{ width: `${Math.max(0, Math.min(100, barValue * 100))}%` }}
          />
        </div>
      ) : null}
    </div>
  );
}

export default async function BenchmarksPage() {
  let overviews: BenchmarkOverview[] = [];

  try {
    overviews = await serverApi.getBenchmarkOverview();
  } catch {
    overviews = [];
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight text-[#1A1410]">
          Benchmarks
        </h1>
        <p className="mt-1 text-sm text-[#9C948A]">
          Suite-level accuracy and reliability metrics.
        </p>
      </div>

      {overviews.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-[#E2DAD0] bg-white py-16 text-center shadow-sm">
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
              d="M5 19V9m7 10V5m7 14v-7"
            />
          </svg>
          <p className="mt-4 text-base font-medium text-[#1A1410]">
            No benchmark runs yet
          </p>
          <Link
            href="/dashboard"
            className="mt-5 inline-flex items-center rounded-xl bg-[#1A1410] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#2D2520]"
          >
            Run your first benchmark →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 mt-6">
          {overviews.map((overview) => (
            <article
              key={overview.suite_id ?? overview.suite_name}
              className="bg-white border border-[#E2DAD0] rounded-2xl p-6 shadow-sm"
            >
              <header>
                <h2 className="text-base font-semibold text-[#1A1410]">
                  {overview.suite_name}
                </h2>
                <p className="text-xs text-[#9C948A] mt-0.5">
                  {overview.run_count} runs
                </p>
              </header>

              <div className="grid grid-cols-2 gap-3 mt-4">
                <MetricCell
                  label="Claim Accuracy"
                  value={percent(overview.claim_accuracy)}
                  valueClassName={rateColor(overview.claim_accuracy)}
                />
                <MetricCell
                  label="Pass Rate"
                  value={percent(overview.verification_pass_rate)}
                  valueClassName={rateColor(overview.verification_pass_rate)}
                />
                <MetricCell
                  label="Retry Rate"
                  value={percent(overview.retry_rate)}
                  valueClassName={rateColor(overview.retry_rate, true)}
                />
                <MetricCell
                  label="Escalation Rate"
                  value={percent(overview.escalation_rate)}
                  valueClassName={rateColor(overview.escalation_rate, true)}
                />
                <MetricCell
                  label="Avg Confidence"
                  value={percent(overview.average_confidence)}
                  valueClassName="text-[#1A1410]"
                  barValue={overview.average_confidence}
                />
                <MetricCell
                  label="False Positive Rate"
                  value={percent(overview.false_positive_rate)}
                  valueClassName={
                    overview.false_positive_rate > 0
                      ? "text-[#991B1B]"
                      : "text-[#166534]"
                  }
                />
                <MetricCell
                  label="False Negative Rate"
                  value={percent(overview.false_negative_rate)}
                  valueClassName={
                    overview.false_negative_rate > 0
                      ? "text-[#991B1B]"
                      : "text-[#166534]"
                  }
                />
                <MetricCell
                  label="Run Count"
                  value={overview.run_count.toString()}
                  valueClassName="text-[#1A1410]"
                />
              </div>

              <div className="mt-5 h-1.5 rounded-full bg-[#E2DAD0]">
                <div
                  className={`h-1.5 rounded-full ${rateBarColor(
                    overview.verification_pass_rate
                  )}`}
                  style={{
                    width: `${Math.max(
                      0,
                      Math.min(100, overview.verification_pass_rate * 100)
                    )}%`,
                  }}
                />
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
