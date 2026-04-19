import type { Escalation } from "@/types/run";

type EscalationPanelProps = {
  escalations: Escalation[];
};

export default function EscalationPanel({ escalations }: EscalationPanelProps) {
  if (escalations.length === 0) {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
        No escalations for this run.
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {escalations.map((escalation) => (
        <article key={escalation.id} className="rounded-[1.5rem] border border-amber-200 bg-amber-50/70 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-amber-700">Escalation</p>
              <h3 className="mt-2 text-lg font-semibold text-slate-950">{escalation.status}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-700">{escalation.failure_reason}</p>
            </div>
            <div className="text-right text-sm text-slate-500">
              <p>{new Date(escalation.created_at).toLocaleString()}</p>
              {escalation.resolved_at ? <p>Resolved {new Date(escalation.resolved_at).toLocaleString()}</p> : null}
            </div>
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Why review was needed</p>
              <div className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                {summarizeEscalation(escalation).map((line) => (
                  <p key={line}>{line}</p>
                ))}
              </div>
            </div>
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Reviewer decisions</p>
              <div className="mt-3 space-y-3">
                {escalation.reviewer_decisions.map((decision) => (
                  <div key={decision.id} className="rounded-2xl border border-slate-200 bg-white p-3">
                    <p className="text-sm font-semibold text-slate-900">
                      {decision.decision} {decision.reviewer_name ? `by ${decision.reviewer_name}` : ""}
                    </p>
                    {decision.notes ? <p className="mt-1 text-sm text-slate-600">{decision.notes}</p> : null}
                  </div>
                ))}
                {escalation.reviewer_decisions.length === 0 ? (
                  <p className="text-sm text-slate-500">No reviewer decision yet.</p>
                ) : null}
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function summarizeEscalation(escalation: Escalation): string[] {
  const evidence = escalation.evidence_bundle ?? {};
  const task = asRecord(evidence.task);
  const actionClaim = asRecord(evidence.action_claim);
  const verification = asRecord(evidence.verification_result);
  const lines: string[] = [];

  if (typeof task?.description === "string") {
    lines.push(`Task: ${task.description}`);
  }
  lines.push(`Reason: ${escalation.failure_reason}`);
  if (typeof actionClaim?.error === "string" && actionClaim.error.trim()) {
    lines.push(`Last executor error: ${actionClaim.error.trim()}`);
  }
  if (typeof verification?.evidence === "string" && verification.evidence.trim()) {
    lines.push(`Verifier evidence: ${verification.evidence.trim()}`);
  }
  if (typeof verification?.judge_reasoning === "string" && verification.judge_reasoning.trim()) {
    lines.push(`Judge note: ${verification.judge_reasoning.trim()}`);
  }

  return lines.slice(0, 5);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : null;
}
