"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

export default function RunForm() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(async () => {
      try {
        const run = await api.createRun(goal, acceptanceCriteria || null);
        router.push(`/runs/${run.id}`);
      } catch (submitError) {
        setError(submitError instanceof Error ? submitError.message : "Failed to create run.");
      }
    });
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-slate-200">Goal</span>
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          required
          rows={4}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-400 focus:border-amber-400"
          placeholder="Describe what VerifyFlow should accomplish."
        />
      </label>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-slate-200">Acceptance Criteria</span>
        <textarea
          value={acceptanceCriteria}
          onChange={(event) => setAcceptanceCriteria(event.target.value)}
          rows={4}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-400 focus:border-amber-400"
          placeholder="Optional: define what success should look like."
        />
      </label>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}

      <button
        type="submit"
        disabled={isPending || goal.trim().length === 0}
        className="rounded-full bg-amber-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:bg-slate-500 disabled:text-slate-200"
      >
        {isPending ? "Creating..." : "Start Run"}
      </button>
    </form>
  );
}
