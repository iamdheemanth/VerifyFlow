import type {
  LedgerEntry,
  Run,
  RunStreamEvent,
  RunSummary,
} from "@/types/run";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  async createRun(goal: string, acceptance_criteria: string | null): Promise<RunSummary> {
    return request<RunSummary>("/runs", {
      method: "POST",
      body: JSON.stringify({ goal, acceptance_criteria }),
    });
  },

  async getRuns(): Promise<RunSummary[]> {
    return request<RunSummary[]>("/runs");
  },

  async getRun(id: string): Promise<Run> {
    return request<Run>(`/runs/${id}`);
  },

  async getLedger(run_id: string): Promise<LedgerEntry[]> {
    return request<LedgerEntry[]>(`/ledger/${run_id}`);
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
