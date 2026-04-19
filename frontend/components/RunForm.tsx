"use client";

import { FormEvent, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import type { BenchmarkCase, ModelPromptConfig } from "@/types/run";

export default function RunForm() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [configs, setConfigs] = useState<ModelPromptConfig[]>([]);
  const [benchmarkCases, setBenchmarkCases] = useState<BenchmarkCase[]>([]);
  const [executorConfigId, setExecutorConfigId] = useState("");
  const [judgeConfigId, setJudgeConfigId] = useState("");
  const [benchmarkCaseId, setBenchmarkCaseId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let cancelled = false;

    async function loadMetadata() {
      try {
        const [configRows, benchmarkRows] = await Promise.all([
          api.getConfigurations(),
          api.getBenchmarkCases(),
        ]);
        if (cancelled) {
          return;
        }
        setConfigs(configRows);
        setBenchmarkCases(benchmarkRows);
      } catch {
        if (!cancelled) {
          setConfigs([]);
          setBenchmarkCases([]);
        }
      }
    }

    void loadMetadata();

    return () => {
      cancelled = true;
    };
  }, []);

  const executorConfigs = useMemo(
    () => configs.filter((config) => config.role === "executor"),
    [configs]
  );
  const judgeConfigs = useMemo(
    () => configs.filter((config) => config.role === "judge"),
    [configs]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(async () => {
      try {
        const run = await api.createRun({
          goal,
          acceptance_criteria: acceptanceCriteria || null,
          executor_config_id: executorConfigId || null,
          judge_config_id: judgeConfigId || null,
          benchmark_case_id: benchmarkCaseId || null,
        });
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

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-slate-200">Executor Config</span>
        <select
          value={executorConfigId}
          onChange={(event) => setExecutorConfigId(event.target.value)}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400"
        >
          <option value="" className="text-slate-950">
            Default executor
          </option>
          {executorConfigs.map((config) => (
            <option key={config.id} value={config.id} className="text-slate-950">
              {config.name} · {config.model_name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-slate-200">Judge Config</span>
        <select
          value={judgeConfigId}
          onChange={(event) => setJudgeConfigId(event.target.value)}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400"
        >
          <option value="" className="text-slate-950">
            Default judge
          </option>
          {judgeConfigs.map((config) => (
            <option key={config.id} value={config.id} className="text-slate-950">
              {config.name} · {config.model_name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-2">
        <span className="text-sm font-medium text-slate-200">Benchmark Case</span>
        <select
          value={benchmarkCaseId}
          onChange={(event) => setBenchmarkCaseId(event.target.value)}
          className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition focus:border-amber-400"
        >
          <option value="" className="text-slate-950">
            Standard run
          </option>
          {benchmarkCases.map((benchmarkCase) => (
            <option key={benchmarkCase.id} value={benchmarkCase.id} className="text-slate-950">
              {benchmarkCase.name}
            </option>
          ))}
        </select>
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
