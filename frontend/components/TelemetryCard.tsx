import type { RunTelemetry } from "@/types/run";

type TelemetryCardProps = {
  telemetry: RunTelemetry | null;
};

type TelemetryStat =
  | {
      label: string;
      value: string;
      valueClassName: string;
      barValue?: never;
    }
  | {
      label: string;
      value: string;
      valueClassName: string;
      barValue: number;
    };

function formatLatency(value: number) {
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }

  return `${Math.round(value)}ms`;
}

function segmentWidth(count: number, total: number) {
  if (total === 0) {
    return 0;
  }

  return (count / total) * 100;
}

export default function TelemetryCard({ telemetry }: TelemetryCardProps) {
  if (telemetry === null) {
    return (
      <section className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
        <h2 className="text-sm font-semibold text-[#F5F4F0]">Telemetry</h2>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <svg
            aria-hidden="true"
            className="h-6 w-6 text-[#6F6D66]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 7v5l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
            />
          </svg>
          <p className="mt-3 text-sm text-[#6F6D66]">No telemetry data yet.</p>
        </div>
      </section>
    );
  }

  const totalVerifications =
    telemetry.deterministic_verifications +
    telemetry.llm_judge_verifications +
    telemetry.hybrid_verifications;

  const stats: TelemetryStat[] = [
    {
      label: "Executor Latency",
      value: formatLatency(telemetry.total_executor_latency_ms),
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
    },
    {
      label: "Verifier Latency",
      value: formatLatency(telemetry.total_verifier_latency_ms),
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
    },
    {
      label: "Total Retries",
      value: `${telemetry.total_retry_count}`,
      valueClassName: `text-base font-semibold font-mono mt-0.5 block ${
        telemetry.total_retry_count > 0 ? "text-[#B45309]" : "text-[#F5F4F0]"
      }`,
    },
    {
      label: "Tool Calls",
      value: `${telemetry.total_tool_calls}`,
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
    },
    {
      label: "Tokens In",
      value: telemetry.total_token_input.toLocaleString(),
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
    },
    {
      label: "Tokens Out",
      value: telemetry.total_token_output.toLocaleString(),
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
    },
    {
      label: "Total Cost",
      value: `$${telemetry.total_estimated_cost_usd.toFixed(4)}`,
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
    },
    {
      label: "Avg Confidence",
      value: `${Math.round(telemetry.average_confidence * 100)}%`,
      valueClassName: "text-base font-semibold font-mono text-[#F5F4F0] mt-0.5 block",
      barValue: telemetry.average_confidence,
    },
  ];

  return (
    <section className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
      <h2 className="text-sm font-semibold text-[#F5F4F0]">Telemetry</h2>
      <p className="mt-1 break-all font-mono text-[10px] text-[#6F6D66]">
        {telemetry.updated_at}
      </p>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {stats.map((stat) => (
          <div key={stat.label} className="min-w-0 rounded-xl bg-[#10100E] p-3">
            <span className="block text-[9px] uppercase tracking-widest text-[#6F6D66]">
              {stat.label}
            </span>
            <span className={`${stat.valueClassName} break-words`}>{stat.value}</span>
            {typeof stat.barValue === "number" ? (
              <div className="mt-2 h-1 w-12 rounded-full bg-[#E2DAD0]">
                <div
                  className={`h-1 rounded-full ${
                    stat.barValue >= 0.8
                      ? "bg-[#166534]"
                      : stat.barValue >= 0.5
                        ? "bg-[#B45309]"
                        : "bg-[#991B1B]"
                  }`}
                  style={{
                    width: `${Math.max(0, Math.min(100, stat.barValue * 100))}%`,
                  }}
                />
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <div className="mt-4">
        <div className="text-[10px] uppercase tracking-widest text-[#6F6D66] mb-2">
          Verification Methods
        </div>
        <div className="flex h-2 w-full overflow-hidden rounded-full bg-[#23231F]">
          <div
            className="bg-[#9C948A]"
            style={{
              width: `${segmentWidth(
                telemetry.deterministic_verifications,
                totalVerifications
              )}%`,
            }}
          />
          <div
            className="bg-[#7C3AED]"
            style={{
              width: `${segmentWidth(
                telemetry.llm_judge_verifications,
                totalVerifications
              )}%`,
            }}
          />
          <div
            className="bg-[#0D9488]"
            style={{
              width: `${segmentWidth(
                telemetry.hybrid_verifications,
                totalVerifications
              )}%`,
            }}
          />
        </div>

        <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-[#6F6D66]">
          <div className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#9C948A]" />
            <span>Deterministic {telemetry.deterministic_verifications}</span>
          </div>
          <div className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#7C3AED]" />
            <span>LLM Judge {telemetry.llm_judge_verifications}</span>
          </div>
          <div className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[#0D9488]" />
            <span>Hybrid {telemetry.hybrid_verifications}</span>
          </div>
        </div>
      </div>
    </section>
  );
}

