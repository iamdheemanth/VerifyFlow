export interface CreateRunRequest {
  goal: string;
  acceptance_criteria: string | null;
  executor_config_id?: string | null;
  judge_config_id?: string | null;
  benchmark_case_id?: string | null;
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

export interface ModelPromptConfig {
  id: string;
  role: "executor" | "judge";
  name: string;
  model_name: string;
  prompt_template: string;
  prompt_version: string;
  config_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface BenchmarkSuite {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface BenchmarkCase {
  id: string;
  suite_id: string;
  name: string;
  goal: string;
  acceptance_criteria: string | null;
  expected_outcome: string | null;
  label_data: Record<string, unknown> | null;
  created_at: string;
}

export interface TaskAttempt {
  id: string;
  run_id: string;
  task_id: string;
  attempt_index: number;
  tool_name: string;
  tool_params: Record<string, unknown>;
  action_claim: Record<string, unknown> | null;
  verification_payload: Record<string, unknown> | null;
  execution_steps: Array<Record<string, unknown>>;
  tool_calls: Array<Record<string, unknown>>;
  claimed_success: boolean | null;
  verification_method: "deterministic" | "llm_judge" | "hybrid" | null;
  final_confidence: number | null;
  executor_latency_ms: number | null;
  verifier_latency_ms: number | null;
  total_latency_ms: number | null;
  token_input: number;
  token_output: number;
  token_total: number;
  estimated_cost_usd: number;
  outcome: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunTelemetry {
  id: string;
  run_id: string;
  total_executor_latency_ms: number;
  total_verifier_latency_ms: number;
  total_task_latency_ms: number;
  total_retry_count: number;
  total_token_input: number;
  total_token_output: number;
  total_token_total: number;
  total_estimated_cost_usd: number;
  total_tool_calls: number;
  deterministic_verifications: number;
  llm_judge_verifications: number;
  hybrid_verifications: number;
  average_confidence: number;
  created_at: string;
  updated_at: string;
}

export interface ReviewerDecision {
  id: string;
  escalation_id: string;
  run_id: string;
  task_id: string;
  reviewer_key: string | null;
  reviewer_display_name: string | null;
  reviewer_name: string | null;
  decision: "approve" | "reject" | "send_back";
  notes: string | null;
  escalation_status: string;
  task_status: string;
  run_status: string;
  reprocess_requested: boolean;
  created_at: string;
}

export interface Escalation {
  id: string;
  run_id: string;
  task_id: string;
  status: "pending_review" | "approved" | "rejected" | "sent_back";
  failure_reason: string;
  evidence_bundle: Record<string, unknown>;
  created_at: string;
  resolved_at: string | null;
  reviewer_decisions: ReviewerDecision[];
}

export interface RunFailureRecord {
  category: string;
  message: string;
  stage?: string;
  original_goal?: string;
  acceptance_criteria?: string | null;
  planner_reason?: string;
  timestamp?: string;
  recorded_at?: string;
  suggested_next_action?: string;
  [key: string]: unknown;
}

export interface Run {
  id: string;
  goal: string;
  acceptance_criteria: string | null;
  status: string;
  kind: "standard" | "benchmark";
  latest_confidence: number | null;
  failure_record: RunFailureRecord | null;
  created_at: string;
  updated_at: string;
  tasks: Task[];
  telemetry: RunTelemetry | null;
  task_attempts: TaskAttempt[];
  escalations: Escalation[];
  reviewer_decisions: ReviewerDecision[];
  executor_config: ModelPromptConfig | null;
  judge_config: ModelPromptConfig | null;
  benchmark_suite: BenchmarkSuite | null;
  benchmark_case: BenchmarkCase | null;
}

export interface RunSummary {
  id: string;
  goal: string;
  status: string;
  kind: "standard" | "benchmark";
  latest_confidence: number | null;
  created_at: string;
  task_count: number;
}

export interface ClaimedVsVerifiedSummary {
  total_tasks: number;
  pending_tasks: number;
  executing_tasks: number;
  claimed_tasks: number;
  verified_tasks: number;
  failed_tasks: number;
  escalated_tasks: number;
}

export interface TaskEvidence {
  task: Task;
  latest_claim: Record<string, unknown> | null;
  latest_verification: Record<string, unknown> | null;
  attempts: TaskAttempt[];
  ledger_entries: LedgerEntry[];
  escalations: Escalation[];
}

export interface TaskInspection extends TaskEvidence {}

export interface RunInspection {
  run: Run;
  claimed_vs_verified: ClaimedVsVerifiedSummary;
  task_inspections: TaskInspection[];
}

export interface LedgerEntry {
  id: string;
  run_id: string;
  task_id: string;
  attempt_id: string | null;
  task_description: string;
  verification_method: "deterministic" | "llm_judge" | "hybrid";
  confidence: number;
  verified: boolean;
  evidence: string;
  judge_reasoning: string | null;
  created_at: string;
}

export interface ReliabilityOverview {
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  escalated_runs: number;
  average_confidence: number;
  total_estimated_cost_usd: number;
  total_tokens: number;
}

export interface BenchmarkOverview {
  suite_id: string | null;
  suite_name: string;
  run_count: number;
  claim_accuracy: number;
  verification_pass_rate: number;
  retry_rate: number;
  escalation_rate: number;
  average_confidence: number;
  false_positive_rate: number;
  false_negative_rate: number;
}

export interface ConfigurationComparison {
  config_id: string;
  role: "executor" | "judge";
  name: string;
  model_name: string;
  prompt_version: string;
  run_count: number;
  success_rate: number;
  escalation_rate: number;
  average_confidence: number;
  average_cost_usd: number;
}

export type RunStreamEvent =
  | { type: "task_update"; task_id: string; status: string }
  | { type: "escalation"; task_id: string; evidence: string; escalation_id?: string }
  | { type: "run_complete"; run_id: string; status?: string }
  | { type: "error"; message: string };
