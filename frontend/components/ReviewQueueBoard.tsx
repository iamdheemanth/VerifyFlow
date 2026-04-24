"use client";

import { useMemo, useState, useTransition } from "react";

import { api } from "@/lib/api";
import type { Escalation } from "@/types/run";

type Decision = "approve" | "reject" | "send_back";

interface ReviewQueueBoardProps {
  initialEscalations: Escalation[];
}

const decisionLabels: Record<Decision, string> = {
  approve: "Approve",
  reject: "Reject",
  send_back: "Send Back",
};

export default function ReviewQueueBoard({ initialEscalations }: ReviewQueueBoardProps) {
  const [escalations, setEscalations] = useState(initialEscalations);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [reviewerNames, setReviewerNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const pendingCount = useMemo(
    () => escalations.filter((escalation) => escalation.status === "pending_review").length,
    [escalations]
  );

  function submitDecision(escalationId: string, decision: Decision) {
    startTransition(async () => {
      setError(null);
      try {
        const reviewerName = reviewerNames[escalationId]?.trim() ?? "";

        const reviewerDecision = await api.submitReviewerDecision(
          escalationId,
          decision,
          notes[escalationId] || null,
          reviewerName,
          reviewerName || null
        );
        setEscalations((current) =>
          current.map((escalation) =>
            escalation.id === escalationId
              ? {
                  ...escalation,
                  status:
                    decision === "approve"
                      ? "approved"
                      : decision === "reject"
                        ? "rejected"
                        : "sent_back",
                  reviewer_decisions: [...escalation.reviewer_decisions, reviewerDecision],
                }
              : escalation
          )
        );
      } catch (submitError) {
        setError(submitError instanceof Error ? submitError.message : "Failed to submit reviewer decision.");
      }
    });
  }

  return (
    <section className="rounded-[2rem] border border-[#2A2A26] bg-[#141412]/80 p-6 shadow-[0_30px_80px_-40px_rgba(15,23,42,0.3)] backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-[#F5F4F0]">Escalation Queue</h2>
          <p className="mt-1 text-sm text-[#6F6D66]">
            Review ambiguous runs without weakening the deterministic-first verification contract.
          </p>
        </div>
        <div className="rounded-full bg-[#C8A882]/10 px-4 py-2 text-sm font-semibold text-[#E8D5BF]">
          {pendingCount} pending review
        </div>
      </div>

      {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

      <div className="mt-6 grid gap-4">
        {escalations.map((escalation) => (
          <article
            key={escalation.id}
            className="rounded-[1.5rem] border border-[#2A2A26] bg-[#10100E] p-5"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-[#6F6D66]">{escalation.run_id}</p>
                <h3 className="mt-2 text-lg font-semibold text-[#F5F4F0]">{escalation.failure_reason}</h3>
              </div>
              <span className="rounded-full bg-[#141412] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[#8A8880]">
                {escalation.status.replace("_", " ")}
              </span>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-[1.25rem] border border-[#2A2A26] bg-[#141412] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[#6F6D66]">Evidence Bundle</p>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-[#8A8880]">
                  {JSON.stringify(escalation.evidence_bundle, null, 2)}
                </pre>
              </div>

              <div className="rounded-[1.25rem] border border-[#2A2A26] bg-[#141412] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-[#6F6D66]">Reviewer Actions</p>
                <div className="mt-3 flex flex-col gap-3">
                  <input
                    value={reviewerNames[escalation.id] ?? ""}
                    onChange={(event) =>
                      setReviewerNames((current) => ({ ...current, [escalation.id]: event.target.value }))
                    }
                    placeholder="Reviewer name"
                    className="rounded-2xl border border-[#2A2A26] px-4 py-3 text-sm text-[#8A8880] outline-none transition focus:border-[#C8A882]"
                  />
                  <textarea
                    value={notes[escalation.id] ?? ""}
                    onChange={(event) =>
                      setNotes((current) => ({ ...current, [escalation.id]: event.target.value }))
                    }
                    rows={4}
                    placeholder="Optional reviewer notes"
                    className="rounded-2xl border border-[#2A2A26] px-4 py-3 text-sm text-[#8A8880] outline-none transition focus:border-[#C8A882]"
                  />
                  <div className="flex flex-wrap gap-2">
                    {(Object.keys(decisionLabels) as Decision[]).map((decision) => (
                      <button
                        key={decision}
                        type="button"
                        disabled={isPending}
                        onClick={() => submitDecision(escalation.id, decision)}
                        className="rounded-full border border-[#2A2A26] bg-[#141412] px-4 py-2 text-sm font-semibold text-[#8A8880] transition hover:bg-[#23231F] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {decisionLabels[decision]}
                      </button>
                    ))}
                  </div>
                </div>

                {escalation.reviewer_decisions.length ? (
                  <div className="mt-4 border-t border-[#2A2A26] pt-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-[#6F6D66]">Decision History</p>
                    <div className="mt-3 grid gap-3">
                      {escalation.reviewer_decisions.map((decision) => (
                        <div key={decision.id} className="rounded-2xl border border-[#2A2A26] bg-[#10100E] p-3">
                          <div className="flex items-center justify-between gap-3">
                            <span className="text-sm font-semibold text-[#F5F4F0]">{decision.decision}</span>
                            <span className="text-xs text-[#6F6D66]">{new Date(decision.created_at).toLocaleString()}</span>
                          </div>
                          <p className="mt-2 text-sm text-[#8A8880]">
                            Reviewer: {decision.reviewer_name || "Unspecified"}
                          </p>
                          {decision.notes ? (
                            <p className="mt-2 text-sm leading-6 text-[#8A8880]">{decision.notes}</p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

