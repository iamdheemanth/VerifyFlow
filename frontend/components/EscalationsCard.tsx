import Link from "next/link";

import StatusBadge from "@/components/StatusBadge";
import type { Escalation } from "@/types/run";

type EscalationsCardProps = {
  escalations: Escalation[];
};

function excerpt(value: string | null, max = 90) {
  if (!value) {
    return "";
  }

  return value.length > max ? `${value.slice(0, max - 3)}...` : value;
}

export default function EscalationsCard({
  escalations,
}: EscalationsCardProps) {
  if (escalations.length === 0) {
    return (
      <section className="rounded-2xl border border-[#E2DAD0] bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-[#1A1410]">Escalations</h2>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <span className="text-[#166534]">✓</span>
          <p className="mt-2 text-sm text-[#9C948A]">No escalations</p>
        </div>
      </section>
    );
  }

  const hasPendingReview = escalations.some(
    (escalation) => escalation.status === "pending_review"
  );

  return (
    <section
      className={`rounded-2xl p-5 shadow-sm ${
        hasPendingReview
          ? "border border-[#C8BEB2] bg-[#FFFBF5]"
          : "border border-[#E2DAD0] bg-white"
      }`}
    >
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-[#1A1410]">Escalations</h2>
        <span className="rounded-full bg-[#FEF3C7] px-2 py-0.5 text-xs text-[#B45309]">
          {escalations.length}
        </span>
      </div>
      <p className="text-xs text-[#9C948A] mt-0.5">Human review required.</p>

      <div className="mt-4">
        {escalations.map((escalation) => {
          const latestDecision =
            escalation.reviewer_decisions[escalation.reviewer_decisions.length - 1];

          return (
            <div
              key={escalation.id}
              className="border-t border-[#E2DAD0] pt-4 mt-4 first:border-t-0 first:pt-0 first:mt-0"
            >
              <StatusBadge status={escalation.status} />
              <p className="text-xs text-[#5C5248] mt-1 leading-5">
                {escalation.failure_reason}
              </p>
              <p className="text-[10px] text-[#9C948A] mt-1">
                {escalation.created_at}
              </p>

              {escalation.status === "pending_review" ? (
                <div className="mt-2 flex items-center justify-between rounded-xl border border-[#FCD34D] bg-[#FEFCE8] px-3 py-2">
                  <span className="text-xs text-[#5C5248]">Needs human review</span>
                  <Link
                    href="/review"
                    className="text-xs font-medium text-[#1D4ED8]"
                  >
                    Review →
                  </Link>
                </div>
              ) : null}

              {latestDecision ? (
                <div className="mt-2">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={latestDecision.decision} />
                    <span className="text-xs text-[#5C5248]">
                      {latestDecision.reviewer_name ?? "Unknown reviewer"}
                    </span>
                  </div>
                  {latestDecision.notes ? (
                    <p className="mt-1 text-xs italic text-[#9C948A]">
                      {excerpt(latestDecision.notes)}
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </section>
  );
}
