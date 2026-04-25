"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import { getApiErrorMessage } from "@/lib/api-error";

export default function DemoSeedButton() {
  const router = useRouter();
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    return () => {
      if (resetTimerRef.current) {
        clearTimeout(resetTimerRef.current);
      }
    };
  }, []);

  function queueReset() {
    if (resetTimerRef.current) {
      clearTimeout(resetTimerRef.current);
    }

    resetTimerRef.current = setTimeout(() => {
      setStatus("idle");
      setErrorMessage(null);
      resetTimerRef.current = null;
    }, 2000);
  }

  return (
    <button
      type="button"
      disabled={isPending}
      onClick={() =>
        startTransition(async () => {
          setStatus("idle");
          setErrorMessage(null);

          try {
            await api.seedDemo();
            setStatus("success");
            router.refresh();
            queueReset();
          } catch (seedError) {
            setErrorMessage(getApiErrorMessage(seedError, "Failed to seed demo data."));
            setStatus("error");
            queueReset();
          }
        })
      }
      className="border border-[#3A3A34] bg-[#141412] hover:bg-[#10100E] text-[#8A8880] text-sm rounded-xl px-3 py-1.5 transition-colors disabled:opacity-50"
    >
      {isPending ? (
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
          Seeding…
        </span>
      ) : status === "success" ? (
        <span className="text-[#166534]">Seeded ✓</span>
      ) : status === "error" ? (
        <span className="text-[#991B1B]" title={errorMessage ?? undefined}>Failed</span>
      ) : (
        "Seed Demo Data"
      )}
    </button>
  );
}

