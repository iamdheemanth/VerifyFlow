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
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <label>
        <span className="block text-[10px] uppercase tracking-widest text-[#9C8C80] mb-1.5">
          Goal
        </span>
        <textarea
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          rows={3}
          required
          placeholder="Describe what the AI agent should accomplish…"
          className="w-full bg-[#2D2520] border border-[#3D3028] rounded-xl px-4 py-3 text-white text-sm placeholder-[#7A6E68] focus:outline-none focus:border-[#6B5B4E] resize-none"
        />
      </label>

      <label>
        <span className="block text-[10px] uppercase tracking-widest text-[#9C8C80] mb-1.5">
          Acceptance Criteria (Optional)
        </span>
        <textarea
          value={acceptanceCriteria}
          onChange={(event) => setAcceptanceCriteria(event.target.value)}
          rows={2}
          placeholder="How should success be judged, if you want to specify it?"
          className="w-full bg-[#2D2520] border border-[#3D3028] rounded-xl px-4 py-3 text-white text-sm placeholder-[#7A6E68] focus:outline-none focus:border-[#6B5B4E] resize-none"
        />
      </label>

      <div>
        <button
          type="submit"
          disabled={isLoading || goal.trim().length === 0}
          className="w-full bg-[#C8A882] hover:bg-[#D4B592] text-[#1A1410] font-semibold rounded-xl py-3 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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

        {error ? <p className="text-[#F87171] text-xs mt-2">{error}</p> : null}
      </div>
    </form>
  );
}
