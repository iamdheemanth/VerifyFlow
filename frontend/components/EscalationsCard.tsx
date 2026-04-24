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
      <section className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
        <h2 className="text-sm font-semibold text-[#F5F4F0]">Escalations</h2>
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <span className="text-[#166534]">✓</span>
          <p className="mt-2 text-sm text-[#6F6D66]">No escalations</p>
        </div>
      </section>
    );
  }

  const hasPendingReview = escalations.some(
    (escalation) => escalation.status === "pending_review"
  );

  return (
    <section
      className={`rounded-2xl p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)] ${
        hasPendingReview
          ? "border border-[#3A3A34] bg-[#141412]"
          : "border border-[#2A2A26] bg-[#141412]"
      }`}
    >
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-[#F5F4F0]">Escalations</h2>
        <span className="rounded-full bg-[#FEF3C7] px-2 py-0.5 text-xs text-[#B45309]">
          {escalations.length}
        </span>
      </div>
      <p className="text-xs text-[#6F6D66] mt-0.5">Human review required.</p>

      <div className="mt-4">
        {escalations.map((escalation) => {
          const latestDecision =
            escalation.reviewer_decisions[escalation.reviewer_decisions.length - 1];

          return (
            <div
              key={escalation.id}
              className="border-t border-[#2A2A26] pt-4 mt-4 first:border-t-0 first:pt-0 first:mt-0"
            >
              <StatusBadge status={escalation.status} />
              <p className="text-xs text-[#8A8880] mt-1 leading-5">
                {escalation.failure_reason}
              </p>
              <p className="text-[10px] text-[#6F6D66] mt-1">
                {escalation.created_at}
              </p>

              {escalation.status === "pending_review" ? (
                <div className="mt-2 flex items-center justify-between rounded-xl border border-[#3A332B] bg-[#FEFCE8] px-3 py-2">
                  <span className="text-xs text-[#8A8880]">Needs human review</span>
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
                    <span className="text-xs text-[#8A8880]">
                      {latestDecision.reviewer_name ?? "Unknown reviewer"}
                    </span>
                  </div>
                  {latestDecision.notes ? (
                    <p className="mt-1 text-xs italic text-[#6F6D66]">
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

