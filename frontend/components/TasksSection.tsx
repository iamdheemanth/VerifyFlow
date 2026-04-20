"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import StatusBadge from "@/components/StatusBadge";
import { api } from "@/lib/api";
import type { Run } from "@/types/run";

type TasksSectionProps = {
  run: Run;
};

function isStreamingStatus(status: string) {
  return status === "pending" || status === "planning" || status === "executing";
}

function taskBorderClass(status: string) {
  if (status === "verified" || status === "completed") {
    return "border-[#166534]";
  }

  if (status === "executing") {
    return "border-[#1D4ED8] animate-pulse";
  }

  if (status === "escalated") {
    return "border-[#B45309]";
  }

  if (status === "failed") {
    return "border-[#991B1B]";
  }

  return "border-[#C8BEB2]";
}

export default function TasksSection({ run }: TasksSectionProps) {
  const router = useRouter();
  const [taskStatuses, setTaskStatuses] = useState<Record<string, string>>(() =>
    Object.fromEntries(run.tasks.map((task) => [task.id, task.status]))
  );
  const [expandedTaskIds, setExpandedTaskIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setTaskStatuses(Object.fromEntries(run.tasks.map((task) => [task.id, task.status])));
  }, [run.tasks]);

  useEffect(() => {
    if (!isStreamingStatus(run.status)) {
      return;
    }

    const cleanup = api.streamRun(run.id, (event) => {
      if (event.type === "task_update") {
        setTaskStatuses((current) => ({
          ...current,
          [event.task_id]: event.status,
        }));
        return;
      }

      if (event.type === "escalation") {
        setTaskStatuses((current) => ({
          ...current,
          [event.task_id]: "escalated",
        }));
        return;
      }

      if (event.type === "run_complete") {
        router.refresh();
      }
    });

    return cleanup;
  }, [router, run.id, run.status]);

  function toggleExpanded(taskId: string) {
    setExpandedTaskIds((current) => {
      const next = new Set(current);
      if (next.has(taskId)) {
        next.delete(taskId);
      } else {
        next.add(taskId);
      }
      return next;
    });
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-[#E2DAD0] bg-white shadow-sm">
      <div className="px-6 py-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-[#1A1410]">Tasks</h2>
          <span className="bg-[#EEE9E1] text-[#5C5248] text-xs rounded-full px-2 py-0.5">
            {run.tasks.length}
          </span>
        </div>
      </div>

      {isStreamingStatus(run.status) ? (
        <div className="px-6 pb-1">
          <div className="h-0.5 bg-[#DBEAFE] rounded-full overflow-hidden">
            <div className="animate-pulse bg-[#1D4ED8] w-1/3 h-full rounded-full" />
          </div>
        </div>
      ) : null}

      <div className="divide-y divide-[#E2DAD0]">
        {run.tasks.map((task, index) => {
          const effectiveStatus = taskStatuses[task.id] ?? task.status;
          const isExpanded = expandedTaskIds.has(task.id);

          return (
            <div key={task.id} className="flex items-start gap-4 py-4 px-6">
              <div
                className={`w-7 h-7 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${taskBorderClass(
                  effectiveStatus
                )}`}
              >
                <span className="text-[10px] font-mono text-[#9C948A]">
                  {index + 1}
                </span>
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[#1A1410]">
                  {task.description}
                </p>
                <p className="text-xs text-[#9C948A] mt-0.5 leading-5">
                  {task.success_criteria}
                </p>
                <span className="inline-flex items-center bg-[#EEE9E1] text-[#5C5248] text-[10px] font-mono px-2 py-0.5 rounded mt-1.5">
                  {task.tool_name}
                </span>

                {task.claimed_result !== null ? (
                  <div className="mt-2">
                    <button
                      type="button"
                      onClick={() => toggleExpanded(task.id)}
                      className="text-xs text-[#1D4ED8] hover:underline underline-offset-2"
                    >
                      {isExpanded ? "Hide claimed result" : "Show claimed result"}
                    </button>
                    {isExpanded ? (
                      <pre className="mt-2 bg-[#EEE9E1] text-[#5C5248] text-[11px] p-3 rounded-xl overflow-auto max-h-40 font-mono">
                        {JSON.stringify(task.claimed_result, null, 2)}
                      </pre>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <div className="flex-shrink-0">
                <StatusBadge status={effectiveStatus} />
                {task.retry_count > 0 ? (
                  <span className="text-[10px] text-[#B45309] font-mono mt-1 block">
                    ↺ {task.retry_count}
                  </span>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
