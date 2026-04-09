import type { LedgerEntry } from "@/types/run";

type LedgerTableProps = {
  entries: LedgerEntry[];
};

function progressTone(confidence: number) {
  if (confidence < 0.5) return "bg-rose-400";
  if (confidence < 0.75) return "bg-amber-400";
  return "bg-emerald-400";
}

function truncateTask(text: string) {
  return text.length > 44 ? `${text.slice(0, 41)}...` : text;
}

export default function LedgerTable({ entries }: LedgerTableProps) {
  if (entries.length === 0) {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
        No verification events yet.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-[1.5rem] border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">Task</th>
            <th className="px-4 py-3 font-medium">Method</th>
            <th className="px-4 py-3 font-medium">Confidence</th>
            <th className="px-4 py-3 font-medium">Verified</th>
            <th className="px-4 py-3 font-medium">Evidence</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {entries.map((entry) => (
            <tr key={entry.id} className="align-top">
              <td className="px-4 py-4 text-slate-700">{truncateTask(entry.task_description)}</td>
              <td className="px-4 py-4">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">
                  {entry.verification_method}
                </span>
              </td>
              <td className="px-4 py-4">
                <div className="w-32">
                  <div className="h-2 overflow-hidden rounded-full bg-slate-200">
                    <div
                      className={`h-full rounded-full ${progressTone(entry.confidence)}`}
                      style={{ width: `${Math.max(0, Math.min(100, entry.confidence * 100))}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-slate-500">{Math.round(entry.confidence * 100)}%</p>
                </div>
              </td>
              <td className="px-4 py-4 text-slate-700">{entry.verified ? "Yes" : "No"}</td>
              <td className="px-4 py-4 text-slate-600">
                <p>{entry.evidence}</p>
                {entry.judge_reasoning ? (
                  <details className="mt-3 rounded-2xl bg-slate-50 p-3">
                    <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Judge reasoning
                    </summary>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                      {entry.judge_reasoning}
                    </p>
                  </details>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
