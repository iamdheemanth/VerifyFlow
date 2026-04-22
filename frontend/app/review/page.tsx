"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import StatusBadge from "@/components/StatusBadge";
import { api, getAuthHeaders } from "@/lib/api";
import type { Escalation } from "@/types/run";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type Decision = "approve" | "reject" | "send_back";

type FormState = Record<
  string,
  {
    reviewerKey: string;
    displayName: string;
    notes: string;
  }
>;

function formatCreatedAt(value: string) {
  return new Date(value).toLocaleString();
}

async function submitReviewerDecision(
  escalationId: string,
  decision: Decision,
  notes: string | null,
  reviewerKey: string
) {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(
    `${BASE_URL}/review/escalations/${escalationId}/decision`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders,
      },
      body: JSON.stringify({
        decision,
        notes,
        reviewer_key: reviewerKey,
      }),
      cache: "no-store",
    }
  );

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
}

export default function ReviewPage() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});
  const [submitted, setSubmitted] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);
  const [formState, setFormState] = useState<FormState>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>(
    {}
  );
  const [activeDecision, setActiveDecision] = useState<
    Record<string, Decision | null>
  >({});

  async function loadEscalations() {
    try {
      setError(null);
      const queue = await api.getEscalationQueue();
      setEscalations(queue);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load escalation queue."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadEscalations();

    const intervalId = window.setInterval(() => {
      void loadEscalations();
    }, 30000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  const pendingCount = useMemo(
    () =>
      escalations.filter((escalation) => escalation.status === "pending_review")
        .length,
    [escalations]
  );

  function updateFormState(
    escalationId: string,
    field: "reviewerKey" | "displayName" | "notes",
    value: string
  ) {
    setFormState((current) => ({
      ...current,
      [escalationId]: {
        reviewerKey: current[escalationId]?.reviewerKey ?? "",
        displayName: current[escalationId]?.displayName ?? "",
        notes: current[escalationId]?.notes ?? "",
        [field]: value,
      },
    }));
  }

  function toggleEvidence(escalationId: string) {
    setExpandedEvidence((current) => ({
      ...current,
      [escalationId]: !current[escalationId],
    }));
  }

  async function handleDecision(escalation: Escalation, decision: Decision) {
    const values = formState[escalation.id] ?? {
      reviewerKey: "",
      displayName: "",
      notes: "",
    };

    if (!values.reviewerKey.trim()) {
      setFormErrors((current) => ({
        ...current,
        [escalation.id]: "Reviewer Key is required.",
      }));
      return;
    }

    setFormErrors((current) => ({
      ...current,
      [escalation.id]: "",
    }));
    setSubmitting((current) => ({
      ...current,
      [escalation.id]: true,
    }));
    setActiveDecision((current) => ({
      ...current,
      [escalation.id]: decision,
    }));

    try {
      await submitReviewerDecision(
        escalation.id,
        decision,
        values.notes.trim() || null,
        values.reviewerKey.trim()
      );

      setSubmitted((current) => ({
        ...current,
        [escalation.id]: true,
      }));
      await loadEscalations();
    } catch (submitError) {
      setFormErrors((current) => ({
        ...current,
        [escalation.id]:
          submitError instanceof Error
            ? submitError.message
            : "Failed to submit decision.",
      }));
    } finally {
      setSubmitting((current) => ({
        ...current,
        [escalation.id]: false,
      }));
      setActiveDecision((current) => ({
        ...current,
        [escalation.id]: null,
      }));
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 md:px-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-[#1A1410]">
            Review Queue
          </h1>
          <p className="mt-1 text-sm text-[#9C948A]">
            Human-in-the-loop decisions for escalated tasks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {pendingCount > 0 ? (
            <span className="rounded-full bg-[#FEF3C7] px-3 py-1 text-sm font-medium text-[#92400E]">
              {pendingCount} pending
            </span>
          ) : null}
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              void loadEscalations();
            }}
            className="inline-flex items-center rounded-xl border border-[#E2DAD0] bg-[#F7F3EE] px-4 py-2 text-sm font-medium text-[#5C5248] transition-colors hover:bg-[#EEE9E1] hover:text-[#1A1410]"
          >
            Refresh
          </button>
        </div>
      </div>

      {error ? (
        <p className="mb-4 text-sm text-[#991B1B]">{error}</p>
      ) : null}

      {!loading && escalations.length === 0 ? (
        <div className="rounded-2xl border border-[#E2DAD0] bg-white py-16 text-center shadow-sm">
          <svg
            aria-hidden="true"
            className="mx-auto h-12 w-12 text-[#166534]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="1.8"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m5 13 4 4L19 7"
            />
          </svg>
          <p className="mt-4 text-base font-medium text-[#1A1410]">
            Queue is clear
          </p>
          <p className="mt-1 text-sm text-[#9C948A]">
            All escalations have been resolved.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {loading && escalations.length === 0 ? (
            <div className="rounded-2xl border border-[#E2DAD0] bg-white px-6 py-8 shadow-sm">
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="space-y-2">
                    <div className="skeleton h-4 w-32" />
                    <div className="skeleton h-3 w-full" />
                    <div className="skeleton h-3 w-2/3" />
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {escalations.map((escalation) => {
            const shortId = escalation.id.slice(-8);
            const formValues = formState[escalation.id] ?? {
              reviewerKey: "",
              displayName: "",
              notes: "",
            };
            const isEvidenceOpen = expandedEvidence[escalation.id] ?? false;
            const isSubmitting = submitting[escalation.id] ?? false;
            const escalationError = formErrors[escalation.id];

            return (
              <div
                key={escalation.id}
                className="overflow-hidden rounded-2xl border border-[#E2DAD0] bg-white shadow-sm"
                style={
                  escalation.status === "pending_review"
                    ? { borderLeft: "4px solid #B45309" }
                    : undefined
                }
              >
                <div className="flex items-center justify-between border-b border-[#E2DAD0] px-6 py-4">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-[#1A1410]">
                      Escalation
                    </span>
                    <span className="rounded-lg bg-[#EEE9E1] px-2 py-1 font-mono text-[10px] text-[#5C5248]">
                      {shortId}
                    </span>
                    <StatusBadge status={escalation.status} />
                  </div>
                  <span className="text-xs text-[#9C948A]">
                    {formatCreatedAt(escalation.created_at)}
                  </span>
                </div>

                <div className="space-y-4 px-6 py-4">
                  <div className="flex flex-wrap gap-4">
                    <Link
                      href={`/runs/${escalation.run_id}`}
                      className="text-xs font-mono text-[#1D4ED8]"
                    >
                      run:{escalation.run_id}
                    </Link>
                    <Link
                      href={`/runs/${escalation.run_id}`}
                      className="text-xs font-mono text-[#1D4ED8]"
                    >
                      task:{escalation.task_id}
                    </Link>
                  </div>

                  <div className="rounded-xl bg-[#EEE9E1] px-4 py-3 text-sm text-[#5C5248]">
                    {escalation.failure_reason}
                  </div>

                  <div>
                    <button
                      type="button"
                      onClick={() => toggleEvidence(escalation.id)}
                      className="text-xs text-[#1D4ED8] hover:underline underline-offset-2"
                    >
                      {isEvidenceOpen ? "Hide evidence" : "Show evidence"}
                    </button>
                    {isEvidenceOpen ? (
                      <pre className="mt-2 max-h-48 overflow-auto rounded-xl bg-[#EEE9E1] p-3 font-mono text-[11px] text-[#5C5248]">
                        {JSON.stringify(escalation.evidence_bundle, null, 2)}
                      </pre>
                    ) : null}
                  </div>
                </div>

                {escalation.status === "pending_review" ? (
                  <div className="border-t border-[#E2DAD0] bg-[#FAFAF9] px-6 py-5">
                    <h2 className="mb-4 text-sm font-medium text-[#1A1410]">
                      Submit Decision
                    </h2>

                    <div className="space-y-3">
                      <label className="block">
                        <span className="mb-1.5 block text-xs text-[#5C5248]">
                          Reviewer Key
                        </span>
                        <input
                          type="text"
                          value={formValues.reviewerKey}
                          onChange={(event) =>
                            updateFormState(
                              escalation.id,
                              "reviewerKey",
                              event.target.value
                            )
                          }
                          className="w-full rounded-xl border border-[#C8BEB2] bg-[#F7F3EE] px-3 py-2 text-sm focus:border-[#9C948A] focus:outline-none"
                        />
                      </label>

                      <label className="block">
                        <span className="mb-1.5 block text-xs text-[#5C5248]">
                          Display Name
                        </span>
                        <input
                          type="text"
                          value={formValues.displayName}
                          onChange={(event) =>
                            updateFormState(
                              escalation.id,
                              "displayName",
                              event.target.value
                            )
                          }
                          className="w-full rounded-xl border border-[#C8BEB2] bg-[#F7F3EE] px-3 py-2 text-sm focus:border-[#9C948A] focus:outline-none"
                        />
                      </label>

                      <label className="block">
                        <span className="mb-1.5 block text-xs text-[#5C5248]">
                          Notes
                        </span>
                        <textarea
                          rows={2}
                          value={formValues.notes}
                          onChange={(event) =>
                            updateFormState(
                              escalation.id,
                              "notes",
                              event.target.value
                            )
                          }
                          className="w-full rounded-xl border border-[#C8BEB2] bg-[#F7F3EE] px-3 py-2 text-sm focus:border-[#9C948A] focus:outline-none"
                        />
                      </label>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-3">
                      {([
                        {
                          decision: "approve" as const,
                          label: "Approve",
                          className:
                            "bg-[#166534] hover:bg-[#14532D] text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors",
                        },
                        {
                          decision: "reject" as const,
                          label: "Reject",
                          className:
                            "bg-[#991B1B] hover:bg-[#7F1D1D] text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors",
                        },
                        {
                          decision: "send_back" as const,
                          label: "Send Back",
                          className:
                            "rounded-xl border border-[#E2DAD0] bg-[#F7F3EE] px-4 py-2 text-sm font-medium text-[#5C5248] transition-colors hover:bg-[#EEE9E1] hover:text-[#1A1410]",
                        },
                      ]).map((button) => {
                        const isActive =
                          isSubmitting &&
                          activeDecision[escalation.id] === button.decision;

                        return (
                          <button
                            key={button.decision}
                            type="button"
                            disabled={isSubmitting}
                            onClick={() =>
                              void handleDecision(escalation, button.decision)
                            }
                            className={`${button.className} disabled:cursor-not-allowed disabled:opacity-60`}
                          >
                            {isActive ? (
                              <span className="inline-flex items-center gap-2">
                                <svg
                                  aria-hidden="true"
                                  className="h-4 w-4 animate-spin"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                >
                                  <circle
                                    className="opacity-25"
                                    cx="12"
                                    cy="12"
                                    r="10"
                                    stroke="currentColor"
                                    strokeWidth="4"
                                  />
                                  <path
                                    className="opacity-90"
                                    fill="currentColor"
                                    d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4Z"
                                  />
                                </svg>
                                Submitting...
                              </span>
                            ) : (
                              button.label
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {submitted[escalation.id] ? (
                      <p className="mt-3 text-xs text-[#166534]">
                        Decision submitted.
                      </p>
                    ) : null}

                    {escalationError ? (
                      <p className="mt-3 text-xs text-[#991B1B]">
                        {escalationError}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {escalation.reviewer_decisions.length > 0 ? (
                  <div className="border-t border-[#E2DAD0] px-6 py-4">
                    <h3 className="mb-3 text-[10px] uppercase tracking-widest text-[#9C948A]">
                      Decision History
                    </h3>
                    <div className="space-y-2">
                      {escalation.reviewer_decisions.map((decision) => (
                        <div
                          key={decision.id}
                          className="flex flex-wrap items-center gap-2 text-xs"
                        >
                          <StatusBadge status={decision.decision} />
                          <span className="font-medium text-[#1A1410]">
                            {decision.reviewer_name ?? "Unknown reviewer"}
                          </span>
                          {decision.notes ? (
                            <span className="truncate italic text-[#9C948A]">
                              {decision.notes}
                            </span>
                          ) : null}
                          <span className="text-[#9C948A]">
                            {formatCreatedAt(decision.created_at)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
