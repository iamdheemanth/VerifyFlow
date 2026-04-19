import type {
  BenchmarkCase,
  BenchmarkOverview,
  BenchmarkSuite,
  ConfigurationComparison,
  CreateRunRequest,
  Escalation,
  LedgerEntry,
  ModelPromptConfig,
  ReliabilityOverview,
  ReviewerDecision,
  Run,
  RunStreamEvent,
  RunSummary,
} from "@/types/run";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init?.headers);

  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  if (response.status === 204 || response.status === 205) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  async createRun(payload: CreateRunRequest): Promise<RunSummary> {
    return request<RunSummary>("/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async seedDemo(): Promise<{ created_runs: number }> {
    return request<{ created_runs: number }>("/demo/seed", { method: "POST" });
  },

  async getRuns(): Promise<RunSummary[]> {
    return request<RunSummary[]>("/runs");
  },

  async getOverview(): Promise<ReliabilityOverview> {
    return request<ReliabilityOverview>("/runs/overview");
  },

  async getRun(id: string): Promise<Run> {
    return request<Run>(`/runs/${id}`);
  },

  async getLedger(run_id: string): Promise<LedgerEntry[]> {
    return request<LedgerEntry[]>(`/ledger/${run_id}`);
  },

  async getEscalationQueue(): Promise<Escalation[]> {
    return request<Escalation[]>("/review/queue");
  },

  async submitReviewerDecision(
    escalationId: string,
    decision: "approve" | "reject" | "send_back",
    notes: string | null,
    reviewer_name: string | null
  ): Promise<ReviewerDecision> {
    return request<ReviewerDecision>(`/review/escalations/${escalationId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, notes, reviewer_name }),
    });
  },

  async getBenchmarkSuites(): Promise<BenchmarkSuite[]> {
    return request<BenchmarkSuite[]>("/benchmarks/suites");
  },

  async getBenchmarkCases(): Promise<BenchmarkCase[]> {
    return request<BenchmarkCase[]>("/benchmarks/cases");
  },

  async getBenchmarkOverview(): Promise<BenchmarkOverview[]> {
    return request<BenchmarkOverview[]>("/benchmarks/overview");
  },

  async getConfigurations(): Promise<ModelPromptConfig[]> {
    return request<ModelPromptConfig[]>("/configurations");
  },

  async getConfigurationComparison(): Promise<ConfigurationComparison[]> {
    return request<ConfigurationComparison[]>("/configurations/comparison");
  },

  async deleteRun(id: string): Promise<void> {
    await request<void>(`/runs/${id}`, { method: "DELETE" });
  },

  async deleteTask(runId: string, taskId: string): Promise<void> {
    await request<void>(`/runs/${runId}/tasks/${taskId}`, { method: "DELETE" });
  },

  streamRun(run_id: string, onEvent: (event: RunStreamEvent) => void): () => void {
    const source = new EventSource(`${BASE_URL}/runs/${run_id}/stream`);

    source.onmessage = (event) => {
      try {
        onEvent(JSON.parse(event.data) as RunStreamEvent);
      } catch {
        onEvent({ type: "error", message: "Failed to parse stream event." });
      }
    };

    source.onerror = () => {
      onEvent({ type: "error", message: "Stream connection error." });
    };

    return () => {
      source.close();
    };
  },
};
