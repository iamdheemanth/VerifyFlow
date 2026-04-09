export interface CreateRunRequest {
  goal: string;
  acceptance_criteria: string | null;
}

export interface Task {
  id: string;
  run_id: string;
  index: number;
  description: string;
  success_criteria: string;
  tool_name: string;
  tool_params: Record<string, unknown>;
  status: string;
  claimed_result: Record<string, unknown> | null;
  retry_count: number;
  created_at: string;
}

export interface Run {
  id: string;
  goal: string;
  acceptance_criteria: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  tasks: Task[];
}

export interface RunSummary {
  id: string;
  goal: string;
  status: string;
  created_at: string;
  task_count: number;
}

export interface LedgerEntry {
  id: string;
  run_id: string;
  task_id: string;
  task_description: string;
  verification_method: "deterministic" | "llm_judge" | "hybrid";
  confidence: number;
  verified: boolean;
  evidence: string;
  judge_reasoning: string | null;
  created_at: string;
}

export type RunStreamEvent =
  | { type: "task_update"; task_id: string; status: string }
  | { type: "escalation"; task_id: string; evidence: string }
  | { type: "run_complete"; run_id: string }
  | { type: "error"; message: string };
