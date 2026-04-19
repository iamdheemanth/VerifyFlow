import type { RunTelemetry } from "@/types/run";

type RunTelemetrySummaryProps = {
  telemetry: RunTelemetry | null;
};

function metric(value: string, label: string) {
  return (
    <div className="rounded-[1.25rem] border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

export default function RunTelemetrySummary({ telemetry }: RunTelemetrySummaryProps) {
  if (!telemetry) {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
        No telemetry captured yet.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {metric(`${Math.round(telemetry.average_confidence * 100)}%`, "Average confidence")}
      {metric(`${telemetry.total_retry_count}`, "Retries")}
      {metric(`${telemetry.total_token_total}`, "Total tokens")}
      {metric(`$${telemetry.total_estimated_cost_usd.toFixed(4)}`, "Estimated cost")}
      {metric(`${Math.round(telemetry.total_task_latency_ms)} ms`, "Total task latency")}
      {metric(`${Math.round(telemetry.total_executor_latency_ms)} ms`, "Executor latency")}
      {metric(`${Math.round(telemetry.total_verifier_latency_ms)} ms`, "Verifier latency")}
      {metric(`${telemetry.total_tool_calls}`, "Tool calls")}
    </div>
  );
}
