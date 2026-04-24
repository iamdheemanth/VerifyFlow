import type { LedgerEntry, Task } from "@/types/run";

type TaskCardProps = {
  task: Task;
  ledgerEntries: LedgerEntry[];
  onDelete?: (taskId: string) => void;
  deleting?: boolean;
};

function cardTone(status: string) {
  if (status === "verified") return "border-emerald-500/30 bg-emerald-500/10";
  if (status === "claimed" || status === "executing") return "border-[#3A332B] bg-[#C8A882]/10";
  if (status === "failed") return "border-[#7F1D1D] bg-[#991B1B]/10";
  if (status === "escalated") return "border-[#7F1D1D] bg-[#991B1B]/15";
  return "border-[#2A2A26] bg-[#141412]";
}

function badgeTone(status: string) {
  if (status === "verified") return "bg-emerald-500/10 text-emerald-300";
  if (status === "claimed" || status === "executing") return "bg-[#C8A882]/10 text-[#E8D5BF]";
  if (status === "failed" || status === "escalated") return "bg-[#991B1B]/15 text-[#FCA5A5]";
  return "bg-[#23231F] text-[#8A8880]";
}

export default function TaskCard({ task, ledgerEntries, onDelete, deleting = false }: TaskCardProps) {
  const taskEntries = ledgerEntries.filter((entry) => entry.task_id === task.id);
  const latestEntry = taskEntries.at(-1);
  const claimedResultSummary = task.claimed_result
    ? JSON.stringify(task.claimed_result).slice(0, 180)
    : null;
  const isClaimedPendingVerification = task.status === "claimed" || task.status === "executing";
  const isDiverged = Boolean(task.claimed_result) && latestEntry && !latestEntry.verified;

  return (
    <article className={`rounded-[1.5rem] border p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)] transition ${cardTone(task.status)} ${isDiverged ? "border-[#7F1D1D]" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-[#6F6D66]">Task {task.index + 1}</p>
          <h3 className="mt-2 text-lg font-semibold text-[#F5F4F0]">{task.description}</h3>
          <p className="mt-2 text-sm leading-6 text-[#8A8880]">{task.success_criteria}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${badgeTone(task.status)}`}>
            {task.status}
          </span>
          {onDelete ? (
            <button
              type="button"
              disabled={deleting}
              onClick={() => onDelete(task.id)}
              className="rounded-full border border-[#7F1D1D] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[#FCA5A5] transition hover:bg-[#991B1B]/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Delete
            </button>
          ) : null}
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.2em] text-[#6F6D66]">
        <span className="rounded-full bg-[#C8A882] px-3 py-1 text-[#0A0A08]">Planned</span>
        <span className={`h-px flex-1 ${task.claimed_result ? "bg-[#3A3A34]" : "bg-[#2A2A26]"}`} />
        <span className={`rounded-full px-3 py-1 ${task.claimed_result ? "bg-[#C8A882]/20 text-[#E8D5BF]" : "bg-[#23231F] text-[#6F6D66]"}`}>
          Claimed
        </span>
        {isClaimedPendingVerification ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-[#C8A882] border-t-transparent" /> : null}
        <span className={`h-px flex-1 ${task.status === "verified" ? "bg-emerald-400" : isDiverged ? "bg-red-300" : "bg-[#2A2A26]"}`} />
        <span className={`rounded-full px-3 py-1 ${task.status === "verified" ? "bg-emerald-500/10 text-emerald-300" : isDiverged ? "bg-red-500/10 text-red-300" : "bg-[#23231F] text-[#6F6D66]"}`}>
          Verified
        </span>
      </div>

      {claimedResultSummary ? (
        <div className="mt-4 border border-[#2A2A26] bg-[#10100E] p-4 text-sm text-[#8A8880]">
          <p className="font-semibold text-[#8A8880]">Claimed result</p>
          <p className="mt-2 break-all font-[family-name:var(--font-geist-mono)] text-xs leading-6">
            {claimedResultSummary}
            {JSON.stringify(task.claimed_result).length > 180 ? "..." : ""}
          </p>
        </div>
      ) : null}

      {task.status === "verified" && latestEntry ? (
        <div className="mt-4 border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
          <p className="font-semibold">Verified</p>
          <p className="mt-1">Confidence {(latestEntry.confidence * 100).toFixed(0)}%</p>
        </div>
      ) : null}

      {(task.status === "failed" || task.status === "escalated" || isDiverged) && latestEntry ? (
        <div className="mt-4 rounded-2xl border border-[#7F1D1D] bg-[#991B1B]/10 p-4 text-sm text-[#FCA5A5]">
          <p className="font-semibold">Verification issue</p>
          <p className="mt-1">{latestEntry.evidence}</p>
        </div>
      ) : null}
    </article>
  );
}


