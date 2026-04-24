import type { TaskAttempt } from "@/types/run";

type AttemptTimelineProps = {
  attempts: TaskAttempt[];
};

export default function AttemptTimeline({ attempts }: AttemptTimelineProps) {
  if (attempts.length === 0) {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-[#2A2A26] bg-[#10100E] px-6 py-10 text-center text-sm text-[#6F6D66]">
        No execution attempts captured yet.
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {attempts.map((attempt) => (
        <article key={attempt.id} className="rounded-[1.5rem] border border-[#2A2A26] bg-[#141412] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#6F6D66]">Attempt {attempt.attempt_index + 1}</p>
              <h3 className="mt-2 text-lg font-semibold text-[#F5F4F0]">{attempt.tool_name}</h3>
              <p className="mt-2 text-sm text-[#8A8880]">Outcome: {attempt.outcome ?? "pending"}</p>
            </div>
            <div className="text-right text-sm text-[#6F6D66]">
              <p>Total {attempt.total_latency_ms ? `${Math.round(attempt.total_latency_ms)} ms` : "—"}</p>
              <p>Confidence {attempt.final_confidence !== null ? `${Math.round(attempt.final_confidence * 100)}%` : "—"}</p>
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <div className="rounded-2xl bg-[#10100E] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#6F6D66]">Claim</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[#8A8880]">
                {summarizeClaim(attempt).map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
            </div>
            <div className="rounded-2xl bg-[#10100E] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#6F6D66]">Verification</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[#8A8880]">
                {summarizeVerification(attempt).map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
            </div>
            <div className="rounded-2xl bg-[#10100E] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#6F6D66]">Telemetry</p>
              <div className="mt-3 space-y-2 text-sm text-[#8A8880]">
                <p>Executor latency: {attempt.executor_latency_ms ? `${Math.round(attempt.executor_latency_ms)} ms` : "—"}</p>
                <p>Verifier latency: {attempt.verifier_latency_ms ? `${Math.round(attempt.verifier_latency_ms)} ms` : "—"}</p>
                <p>Tokens: {attempt.token_total}</p>
                <p>Cost: ${attempt.estimated_cost_usd.toFixed(4)}</p>
                <p>Tool calls: {attempt.tool_calls.length}</p>
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function summarizeClaim(attempt: TaskAttempt): string[] {
  const claim = attempt.action_claim ?? {};
  const params = attempt.tool_params ?? {};
  const lines: string[] = [];

  if (typeof params.url === "string") {
    lines.push(`Opened ${params.url}.`);
  }
  if (typeof params.value === "string") {
    lines.push(`Entered "${params.value}".`);
  }
  if (Array.isArray((params as Record<string, unknown>).selectors)) {
    const selectors = ((params as Record<string, unknown>).selectors as unknown[])
      .filter((value): value is string => typeof value === "string")
      .slice(0, 2);
    if (selectors.length) {
      lines.push(`Tried selectors: ${selectors.join(", ")}.`);
    }
  }
  if (claim.claimed_success === true) {
    lines.push("Executor reported success.");
  } else if (claim.claimed_success === false) {
    lines.push("Executor reported failure.");
  }
  if (typeof claim.error === "string" && claim.error.trim()) {
    lines.push(`Last error: ${claim.error.trim()}`);
  }
  if (lines.length === 0) {
    lines.push("No executor claim details were recorded.");
  }
  return lines;
}

function summarizeVerification(attempt: TaskAttempt): string[] {
  const verification = attempt.verification_payload ?? {};
  const lines: string[] = [];

  if (typeof verification.method === "string") {
    lines.push(`Method: ${verification.method}.`);
  }
  if (typeof verification.verified === "boolean") {
    lines.push(verification.verified ? "Verifier marked this attempt as verified." : "Verifier did not verify this attempt.");
  }
  if (typeof verification.confidence === "number") {
    lines.push(`Confidence: ${Math.round(verification.confidence * 100)}%.`);
  }
  if (typeof verification.evidence === "string" && verification.evidence.trim()) {
    lines.push(verification.evidence.trim());
  }
  if (typeof verification.judge_reasoning === "string" && verification.judge_reasoning.trim()) {
    lines.push(`Judge note: ${verification.judge_reasoning.trim()}`);
  }
  if (lines.length === 0) {
    lines.push("No verification details were recorded.");
  }
  return lines.slice(0, 5);
}

