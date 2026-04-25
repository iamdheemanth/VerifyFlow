"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { getApiErrorMessage } from "@/lib/api-error";
import { api } from "@/lib/api";
import type { BenchmarkCase, BenchmarkSuite, RunSummary } from "@/types/run";

type ActionState =
  | { kind: "idle"; message: null }
  | { kind: "success"; message: string }
  | { kind: "warning"; message: string }
  | { kind: "error"; message: string };

function getSuiteName(caseItem: BenchmarkCase, suitesById: Map<string, BenchmarkSuite>) {
  return suitesById.get(caseItem.suite_id)?.name ?? "Benchmark suite";
}

const ACTIVE_BENCHMARK_STATUSES = new Set([
  "queued",
  "pending",
  "planning",
  "executing",
  "verifying",
  "running",
]);

function activeBenchmarkRuns(runs: RunSummary[]) {
  return runs.filter(
    (run) => run.kind === "benchmark" && ACTIVE_BENCHMARK_STATUSES.has(run.status)
  );
}

export default function BenchmarkControls({
  cases,
  suites,
  hasRuns,
}: {
  cases: BenchmarkCase[];
  suites: BenchmarkSuite[];
  hasRuns: boolean;
}) {
  const router = useRouter();
  const [seedState, setSeedState] = useState<ActionState>({ kind: "idle", message: null });
  const [caseState, setCaseState] = useState<ActionState>({ kind: "idle", message: null });
  const [selectedSuiteId, setSelectedSuiteId] = useState<string>("");
  const [suiteName, setSuiteName] = useState("");
  const [caseName, setCaseName] = useState("");
  const [goal, setGoal] = useState("");
  const [acceptanceCriteria, setAcceptanceCriteria] = useState("");
  const [runningCaseId, setRunningCaseId] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [activeBenchmarkRunCount, setActiveBenchmarkRunCount] = useState(0);
  const [isSeeding, startSeedTransition] = useTransition();
  const [isCreatingCase, startCreateCaseTransition] = useTransition();
  const [isRunning, startRunTransition] = useTransition();
  const pollInFlightRef = useRef(false);
  const isPollingRef = useRef(false);

  const suitesById = useMemo(
    () => new Map(suites.map((suite) => [suite.id, suite])),
    [suites]
  );

  useEffect(() => {
    isPollingRef.current = isPolling;
  }, [isPolling]);

  const refreshBenchmarkData = useCallback(async () => {
    await Promise.allSettled([
      api.getBenchmarkOverview(),
      api.getBenchmarkSuites(),
      api.getBenchmarkCases(),
    ]);
    router.refresh();
  }, [router]);

  const pollBenchmarkRuns = useCallback(
    async ({ forceRefresh = false }: { forceRefresh?: boolean } = {}) => {
      if (pollInFlightRef.current) {
        return;
      }

      pollInFlightRef.current = true;
      try {
        const runs = await api.getRuns();
        const activeRuns = activeBenchmarkRuns(runs);
        setActiveBenchmarkRunCount(activeRuns.length);
        setIsPolling(activeRuns.length > 0);

        if (activeRuns.length > 0 || forceRefresh || isPollingRef.current) {
          await refreshBenchmarkData();
        }
      } catch (error) {
        setRunError(getApiErrorMessage(error, "Failed to refresh benchmark status."));
        setIsPolling(false);
        setActiveBenchmarkRunCount(0);
      } finally {
        pollInFlightRef.current = false;
      }
    },
    [refreshBenchmarkData]
  );

  useEffect(() => {
    void pollBenchmarkRuns();
  }, [pollBenchmarkRuns]);

  useEffect(() => {
    if (!isPolling) {
      return;
    }

    const interval = setInterval(() => {
      void pollBenchmarkRuns();
    }, 2500);

    return () => clearInterval(interval);
  }, [isPolling, pollBenchmarkRuns]);

  function seedDemoBenchmarks() {
    startSeedTransition(async () => {
      setSeedState({ kind: "idle", message: null });

      try {
        const result = await api.seedDemo();
        if (result.created_runs === 0) {
          setSeedState({
            kind: "warning",
            message: result.message ?? "No new demo data was created. Demo data may already exist for this account.",
          });
        } else {
          setSeedState({
            kind: "success",
            message: result.message ?? `Created ${result.created_runs} demo run${result.created_runs === 1 ? "" : "s"}.`,
          });
        }
        router.refresh();
      } catch (error) {
        setSeedState({
          kind: "error",
          message: getApiErrorMessage(error, "Failed to seed demo benchmarks."),
        });
      }
    });
  }

  function runBenchmark(caseItem: BenchmarkCase) {
    startRunTransition(async () => {
      setRunningCaseId(caseItem.id);
      setRunError(null);

      try {
        const run = await api.createRun({
          goal: caseItem.goal,
          acceptance_criteria: caseItem.acceptance_criteria,
          benchmark_case_id: caseItem.id,
        });
        setRunError(null);
        setCaseState({
          kind: "success",
          message: `Benchmark run queued. Make sure the worker is running. Run id: ${run.id}`,
        });
        setActiveBenchmarkRunCount((count) => Math.max(1, count));
        setIsPolling(true);
        router.refresh();
        void pollBenchmarkRuns({ forceRefresh: true });
      } catch (error) {
        setRunError(getApiErrorMessage(error, "Failed to start benchmark run."));
      } finally {
        setRunningCaseId(null);
      }
    });
  }

  function createBenchmarkCase() {
    startCreateCaseTransition(async () => {
      setCaseState({ kind: "idle", message: null });

      try {
        const created = await api.createBenchmarkCase({
          suite_id: selectedSuiteId || null,
          suite_name: selectedSuiteId ? null : suiteName,
          name: caseName,
          goal,
          acceptance_criteria: acceptanceCriteria || null,
          expected_outcome: "completed",
        });
        setCaseName("");
        setGoal("");
        setAcceptanceCriteria("");
        if (!selectedSuiteId) {
          setSuiteName("");
        }
        setCaseState({
          kind: "success",
          message: `Benchmark case "${created.name}" created.`,
        });
        router.refresh();
      } catch (error) {
        setCaseState({
          kind: "error",
          message: getApiErrorMessage(error, "Failed to create benchmark case."),
        });
      }
    });
  }

  const caseStateClass =
    caseState.kind === "error"
      ? "text-[#FCA5A5]"
      : caseState.kind === "warning"
        ? "text-[#FCD34D]"
        : "text-[#86EFAC]";

  return (
    <div className="mt-6 space-y-6">
      {!hasRuns ? (
        <section className="rounded-2xl border border-[#2A2A26] bg-[#141412] px-6 py-10 text-center shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]">
          <p className="text-base font-medium text-[#F5F4F0]">No benchmark runs yet</p>
          <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-[#8A8880]">
            Seed the demo data to see a completed benchmark overview, or start a queued benchmark from one of the cases below.
          </p>
          <button
            type="button"
            onClick={seedDemoBenchmarks}
            disabled={isSeeding}
            className="mt-5 inline-flex items-center justify-center rounded-xl bg-[#C8A882] px-4 py-2.5 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSeeding ? "Seeding demo benchmarks..." : "Seed demo benchmarks"}
          </button>
          {seedState.message ? (
            <p
              className={`mx-auto mt-3 max-w-2xl text-sm ${
                seedState.kind === "error"
                  ? "text-[#FCA5A5]"
                  : seedState.kind === "warning"
                    ? "text-[#FCD34D]"
                    : "text-[#86EFAC]"
              }`}
            >
              {seedState.message}
            </p>
          ) : null}
        </section>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#2A2A26] bg-[#141412] px-5 py-4">
          <div>
            <p className="text-sm font-medium text-[#F5F4F0]">Demo benchmark data</p>
            <p className="mt-0.5 text-xs text-[#8A8880]">Seed example runs again only when this user has no existing runs.</p>
          </div>
          <button
            type="button"
            onClick={seedDemoBenchmarks}
            disabled={isSeeding}
            className="rounded-xl border border-[#3A3A34] px-3 py-2 text-sm font-medium text-[#F5F4F0] transition-colors hover:bg-[#1F1F1B] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSeeding ? "Seeding..." : "Seed demo benchmarks"}
          </button>
          {seedState.message ? (
            <p
              className={`basis-full text-sm ${
                seedState.kind === "error"
                  ? "text-[#FCA5A5]"
                  : seedState.kind === "warning"
                    ? "text-[#FCD34D]"
                    : "text-[#86EFAC]"
              }`}
            >
              {seedState.message}
            </p>
          ) : null}
        </div>
      )}

      {isPolling ? (
        <div className="rounded-2xl border border-[#3A3A34] bg-[#10100E] px-4 py-3 text-sm text-[#F5F4F0]">
          Benchmark run in progress{activeBenchmarkRunCount > 1 ? ` (${activeBenchmarkRunCount})` : ""}. Metrics refresh automatically.
        </div>
      ) : null}

      <section>
        <div className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-xl font-semibold tracking-tight text-[#F5F4F0]">New benchmark case</h2>
              <p className="mt-1 text-sm text-[#6F6D66]">
                Create a saved case, then run it to generate benchmark results.
              </p>
            </div>
            <span className="rounded-full bg-[#24231F] px-3 py-1 text-xs font-medium text-[#C8A882]">
              Worker required for execution
            </span>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block">
              <span className="text-xs uppercase tracking-widest text-[#6F6D66]">Suite</span>
              <select
                value={selectedSuiteId}
                onChange={(event) => setSelectedSuiteId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-[#3A3A34] bg-[#10100E] px-3 py-2 text-sm text-[#F5F4F0] outline-none focus:border-[#C8A882]"
              >
                <option value="">Create or use suite name below</option>
                {suites.map((suite) => (
                  <option key={suite.id} value={suite.id}>
                    {suite.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="block">
              <span className="text-xs uppercase tracking-widest text-[#6F6D66]">Suite name</span>
              <input
                value={suiteName}
                onChange={(event) => setSuiteName(event.target.value)}
                disabled={Boolean(selectedSuiteId)}
                placeholder="Local Smoke Suite"
                className="mt-2 w-full rounded-xl border border-[#3A3A34] bg-[#10100E] px-3 py-2 text-sm text-[#F5F4F0] outline-none placeholder:text-[#6F6D66] focus:border-[#C8A882] disabled:opacity-50"
              />
            </label>

            <label className="block">
              <span className="text-xs uppercase tracking-widest text-[#6F6D66]">Case name</span>
              <input
                value={caseName}
                onChange={(event) => setCaseName(event.target.value)}
                placeholder="Filesystem smoke check"
                className="mt-2 w-full rounded-xl border border-[#3A3A34] bg-[#10100E] px-3 py-2 text-sm text-[#F5F4F0] outline-none placeholder:text-[#6F6D66] focus:border-[#C8A882]"
              />
            </label>

            <label className="block">
              <span className="text-xs uppercase tracking-widest text-[#6F6D66]">Acceptance criteria</span>
              <input
                value={acceptanceCriteria}
                onChange={(event) => setAcceptanceCriteria(event.target.value)}
                placeholder="The requested evidence is verified"
                className="mt-2 w-full rounded-xl border border-[#3A3A34] bg-[#10100E] px-3 py-2 text-sm text-[#F5F4F0] outline-none placeholder:text-[#6F6D66] focus:border-[#C8A882]"
              />
            </label>

            <label className="block md:col-span-2">
              <span className="text-xs uppercase tracking-widest text-[#6F6D66]">Goal</span>
              <textarea
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                placeholder="Create a file named benchmark.txt in /tmp/verifyflow with the content benchmark passed"
                rows={3}
                className="mt-2 w-full resize-none rounded-xl border border-[#3A3A34] bg-[#10100E] px-3 py-2 text-sm leading-6 text-[#F5F4F0] outline-none placeholder:text-[#6F6D66] focus:border-[#C8A882]"
              />
            </label>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={createBenchmarkCase}
              disabled={isCreatingCase}
              className="rounded-xl bg-[#C8A882] px-4 py-2.5 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-[#D4B592] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isCreatingCase ? "Creating..." : "Create benchmark case"}
            </button>
            <p className="text-xs text-[#8A8880]">
              Running a case creates a queued benchmark run for the worker.
            </p>
          </div>

          {caseState.message ? <p className={`mt-3 text-sm ${caseStateClass}`}>{caseState.message}</p> : null}
        </div>

        <div className="mt-8 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-[#F5F4F0]">Benchmark cases</h2>
            <p className="mt-1 text-sm text-[#6F6D66]">
              Start a benchmark run from a saved case. Runs are queued for the worker.
            </p>
          </div>
          <span className="text-xs uppercase tracking-widest text-[#6F6D66]">{cases.length} cases</span>
        </div>

        {cases.length === 0 ? (
          <div className="mt-4 rounded-2xl border border-[#2A2A26] bg-[#141412] px-5 py-6">
            <p className="text-sm font-medium text-[#F5F4F0]">No benchmark cases found</p>
            <p className="mt-1 text-sm text-[#8A8880]">
              Use the seed button to create the demo suite, then refresh this page.
            </p>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {cases.map((caseItem) => {
              const isThisCaseRunning = isRunning && runningCaseId === caseItem.id;
              return (
                <article
                  key={caseItem.id}
                  className="rounded-2xl border border-[#2A2A26] bg-[#141412] p-5 shadow-[0_20px_70px_-58px_rgba(0,0,0,0.95)]"
                >
                  <div className="flex min-h-40 flex-col">
                    <div>
                      <p className="text-xs uppercase tracking-widest text-[#6F6D66]">
                        {getSuiteName(caseItem, suitesById)}
                      </p>
                      <h3 className="mt-2 text-base font-semibold text-[#F5F4F0]">{caseItem.name}</h3>
                      <p className="mt-2 line-clamp-3 text-sm leading-6 text-[#8A8880]">{caseItem.goal}</p>
                    </div>

                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <span className="rounded-full bg-[#24231F] px-3 py-1 text-xs font-medium text-[#C8A882]">
                        Expected {caseItem.expected_outcome ?? "not labelled"}
                      </span>
                      <button
                        type="button"
                        onClick={() => runBenchmark(caseItem)}
                        disabled={isRunning}
                        className="rounded-xl bg-[#F5F4F0] px-3 py-2 text-sm font-semibold text-[#0A0A08] transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isThisCaseRunning ? "Starting..." : "Run benchmark"}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {runError ? <p className="mt-3 text-sm text-[#FCA5A5]">{runError}</p> : null}
      </section>
    </div>
  );
}
