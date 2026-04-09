import type { LedgerEntry, Task } from "@/types/run";

type TaskCardProps = {
  task: Task;
  ledgerEntries: LedgerEntry[];
};

function cardTone(status: string) {
  if (status === "verified") return "border-emerald-200 bg-emerald-50/70";
  if (status === "claimed" || status === "executing") return "border-amber-200 bg-amber-50/70";
  if (status === "failed") return "border-rose-200 bg-rose-50/70";
  if (status === "escalated") return "border-rose-300 bg-rose-100/70";
  return "border-slate-200 bg-white";
}

function badgeTone(status: string) {
  if (status === "verified") return "bg-emerald-100 text-emerald-800";
  if (status === "claimed" || status === "executing") return "bg-amber-100 text-amber-800";
  if (status === "failed" || status === "escalated") return "bg-rose-100 text-rose-800";
  return "bg-slate-100 text-slate-700";
}

export default function TaskCard({ task, ledgerEntries }: TaskCardProps) {
  const taskEntries = ledgerEntries.filter((entry) => entry.task_id === task.id);
  const latestEntry = taskEntries.at(-1);
  const claimedResultSummary = task.claimed_result
    ? JSON.stringify(task.claimed_result).slice(0, 180)
    : null;
  const isClaimedPendingVerification = task.status === "claimed" || task.status === "executing";
  const isDiverged = Boolean(task.claimed_result) && latestEntry && !latestEntry.verified;

  return (
    <article className={`rounded-[1.5rem] border p-5 shadow-sm transition ${cardTone(task.status)} ${isDiverged ? "border-rose-300" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Task {task.index + 1}</p>
          <h3 className="mt-2 text-lg font-semibold text-slate-950">{task.description}</h3>
          <p className="mt-2 text-sm leading-6 text-slate-600">{task.success_criteria}</p>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${badgeTone(task.status)}`}>
          {task.status}
        </span>
      </div>

      <div className="mt-5 flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
        <span className="rounded-full bg-slate-900 px-3 py-1 text-white">Planned</span>
        <span className={`h-px flex-1 ${task.claimed_result ? "bg-slate-400" : "bg-slate-200"}`} />
        <span className={`rounded-full px-3 py-1 ${task.claimed_result ? "bg-amber-200 text-amber-900" : "bg-slate-100 text-slate-400"}`}>
          Claimed
        </span>
        {isClaimedPendingVerification ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-amber-400 border-t-transparent" /> : null}
        <span className={`h-px flex-1 ${task.status === "verified" ? "bg-emerald-400" : isDiverged ? "bg-rose-400" : "bg-slate-200"}`} />
        <span className={`rounded-full px-3 py-1 ${task.status === "verified" ? "bg-emerald-200 text-emerald-900" : isDiverged ? "bg-rose-200 text-rose-900" : "bg-slate-100 text-slate-400"}`}>
          Verified
        </span>
      </div>

      {claimedResultSummary ? (
        <div className="mt-4 rounded-2xl bg-slate-950/5 p-4 text-sm text-slate-600">
          <p className="font-semibold text-slate-700">Claimed result</p>
          <p className="mt-2 break-all font-[family-name:var(--font-geist-mono)] text-xs leading-6">
            {claimedResultSummary}
            {JSON.stringify(task.claimed_result).length > 180 ? "..." : ""}
          </p>
        </div>
      ) : null}

      {task.status === "verified" && latestEntry ? (
        <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <p className="font-semibold">Verified</p>
          <p className="mt-1">Confidence {(latestEntry.confidence * 100).toFixed(0)}%</p>
        </div>
      ) : null}

      {(task.status === "failed" || task.status === "escalated" || isDiverged) && latestEntry ? (
        <div className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
          <p className="font-semibold">Verification issue</p>
          <p className="mt-1">{latestEntry.evidence}</p>
        </div>
      ) : null}
    </article>
  );
}
