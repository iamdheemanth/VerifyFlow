"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { api } from "@/lib/api";

export default function DemoSeedButton() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        disabled={isPending}
        onClick={() =>
          startTransition(async () => {
            setMessage(null);
            try {
              const result = await api.seedDemo();
              setMessage(result.created_runs > 0 ? `Seeded ${result.created_runs} demo runs.` : "Demo data already exists.");
              router.refresh();
            } catch (error) {
              setMessage(error instanceof Error ? error.message : "Failed to seed demo data.");
            }
          })
        }
        className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Seeding..." : "Seed Demo Data"}
      </button>
      {message ? <p className="text-xs text-slate-500">{message}</p> : null}
    </div>
  );
}
