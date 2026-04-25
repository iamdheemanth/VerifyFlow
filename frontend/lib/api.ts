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
  RunInspection,
  RunStreamEvent,
  RunSummary,
} from "@/types/run";

import { createApiError } from "@/lib/api-error";
import { publicEnv } from "@/lib/env";

const BASE_URL = publicEnv.apiUrl;

let _cachedToken: string | null = null;
let _tokenFetchedAt: number = 0;
const TOKEN_TTL_MS = 5 * 60 * 1000; // re-fetch every 5 minutes
const STREAM_RECONNECT_DELAY_MS = 1000;
const STREAM_MAX_RECONNECT_ATTEMPTS = 3;

async function getApiToken(): Promise<string | null> {
  const now = Date.now();
  if (_cachedToken && now - _tokenFetchedAt < TOKEN_TTL_MS) {
    return _cachedToken;
  }
  try {
    const res = await fetch("/api/auth/token");
    if (!res.ok) return null;
    const data = await res.json();
    _cachedToken = data.token ?? null;
    _tokenFetchedAt = now;
    return _cachedToken;
  } catch {
    return null;
  }
}

export async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await getApiToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

function parseStreamEvent(block: string): RunStreamEvent | null {
  const data = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n")
    .trim();

  if (!data) {
    return null;
  }

  return JSON.parse(data) as RunStreamEvent;
}

async function readRunStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: RunStreamEvent) => void,
  signal: AbortSignal
): Promise<boolean> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let sawTerminalEvent = false;

  try {
    while (!signal.aborted) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        try {
          const event = parseStreamEvent(part);
          if (event) {
            if (event.type === "run_complete") {
              sawTerminalEvent = true;
            }
            onEvent(event);
          }
        } catch {
          onEvent({ type: "error", message: "Failed to parse stream event." });
        }
      }
    }

    buffer += decoder.decode();
    const trailingEvent = parseStreamEvent(buffer);
    if (trailingEvent) {
      if (trailingEvent.type === "run_complete") {
        sawTerminalEvent = true;
      }
      onEvent(trailingEvent);
    }
  } finally {
    reader.releaseLock();
  }

  return sawTerminalEvent;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method?.toUpperCase() ?? "GET";
  const headers = new Headers(init?.headers);

  if (method !== "GET" && method !== "HEAD" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = await getApiToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    throw await createApiError(response, { path });
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

  async getRunInspection(id: string): Promise<RunInspection> {
    return request<RunInspection>(`/runs/${id}/inspection`);
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
    reviewer_key: string,
    reviewer_display_name?: string | null
  ): Promise<ReviewerDecision> {
    return request<ReviewerDecision>(`/review/escalations/${escalationId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, notes, reviewer_key, reviewer_display_name }),
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
    let closed = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let activeController: AbortController | null = null;

    const cleanup = () => {
      closed = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      activeController?.abort();
      activeController = null;
    };

    const scheduleReconnect = (attempt: number, message: string) => {
      if (closed) {
        return;
      }

      if (attempt >= STREAM_MAX_RECONNECT_ATTEMPTS) {
        onEvent({ type: "error", message });
        return;
      }

      onEvent({ type: "error", message: `${message} Reconnecting...` });
      reconnectTimer = setTimeout(() => {
        reconnectTimer = null;
        void connect(attempt + 1);
      }, STREAM_RECONNECT_DELAY_MS);
    };

    const connect = async (attempt: number) => {
      const path = `/runs/${encodeURIComponent(run_id)}/stream`;
      const token = await getApiToken();
      if (!token) {
        onEvent({ type: "error", message: "Authentication is required to stream this run." });
        return;
      }

      const controller = new AbortController();
      activeController = controller;

      try {
        const response = await fetch(`${BASE_URL}${path}`, {
          headers: {
            Accept: "text/event-stream",
            Authorization: `Bearer ${token}`,
          },
          cache: "no-store",
          signal: controller.signal,
        });

        if (response.status === 401) {
          _cachedToken = null;
          const error = await createApiError(response, { path, operation: "Open run stream" });
          scheduleReconnect(attempt, error.message);
          return;
        }

        if (response.status === 403) {
          const error = await createApiError(response, { path, operation: "Open run stream" });
          onEvent({ type: "error", message: error.message });
          return;
        }

        if (response.status === 404) {
          const error = await createApiError(response, { path, operation: "Open run stream" });
          onEvent({ type: "error", message: error.message });
          return;
        }

        if (!response.ok || !response.body) {
          throw await createApiError(response, { path, operation: "Open run stream" });
        }

        const completed = await readRunStream(response.body, onEvent, controller.signal);
        if (!closed && !completed) {
          scheduleReconnect(attempt, "Run stream disconnected.");
        }
      } catch (streamError) {
        if (closed || controller.signal.aborted) {
          return;
        }

        const message =
          streamError instanceof Error && streamError.message
            ? streamError.message
            : "Stream connection error.";
        scheduleReconnect(attempt, message);
      } finally {
        if (activeController === controller) {
          activeController = null;
        }
      }
    };

    void connect(0);
    return cleanup;
  },
};
