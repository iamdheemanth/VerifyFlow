"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

export default function RunForm() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const result = await api.createRun({
        goal,
        acceptance_criteria: acceptanceCriteria || null,
      });
      router.push(`/runs/${result.id}`);
    } catch (submitError) {
      setError(
        submitError instanceof Error ? submitError.message : "Failed to create run."
      );
      setIsLoading(false);
    }
  }

  return (
    <form className="flex flex-col gap-5" onSubmit={handleSubmit}>
      <label>
        <span className="mb-1.5 block text-[10px] uppercase tracking-widest text-[#8A8880]">
          Goal
        </span>
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          rows={3}
          required
          placeholder="Describe what the AI agent should accomplish…"
          className="w-full resize-none rounded-2xl border border-[#2A2A26] bg-[#10100E] px-4 py-3 text-sm text-[#F5F4F0] placeholder-[#6F6D66] outline-none transition-colors hover:border-[#3A3A34] focus:border-[#C8A882] focus:ring-2 focus:ring-[#C8A882]/20"
        />
      </label>

      <label>
        <span className="mb-1.5 block text-[10px] uppercase tracking-widest text-[#8A8880]">
          Acceptance Criteria (Optional)
        </span>
        <textarea
          value={acceptanceCriteria}
          onChange={(event) => setAcceptanceCriteria(event.target.value)}
          rows={2}
          placeholder="How should success be judged, if you want to specify it?"
          className="w-full resize-none rounded-2xl border border-[#2A2A26] bg-[#10100E] px-4 py-3 text-sm text-[#F5F4F0] placeholder-[#6F6D66] outline-none transition-colors hover:border-[#3A3A34] focus:border-[#C8A882] focus:ring-2 focus:ring-[#C8A882]/20"
        />
      </label>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <button
          type="submit"
          disabled={isLoading || goal.trim().length === 0}
          className="inline-flex items-center justify-center rounded-xl bg-[#C8A882] px-6 py-3 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
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
              Starting…
            </span>
          ) : (
            "Start Run →"
          )}
        </button>

        {error ? <p className="text-xs text-[#F87171]">{error}</p> : null}
      </div>
    </form>
  );
}
