/// <reference types="vite/client" />
/**
 * Typed fetch client for the Datalake HTTP API.
 *
 * The Python server (datalake/api/server.py) returns JSON shaped to match
 * `frontend/src/data/mock.ts` exactly, so call-sites swap one import for
 * another and keep their existing types.
 *
 * The base URL is read from `VITE_API_BASE` (set in `frontend/.env.local`) and
 * defaults to `http://localhost:8000` to match the `datalake api` default port.
 */

import type {
  CatalogRow,
  StreamItem,
} from "@/data/mock";

const BASE =
  (import.meta.env as Record<string, string | undefined>).VITE_API_BASE ??
  "http://localhost:8000";

export type RunSummary = {
  id: string;
  started_at: number;
  ended_at: number | null;
  corpus_version: string | null;
};

export type Counters = {
  run_id: string;
  docs_done: number;
  docs_failed: number;
  docs_partial: number;
  wafer_usd: number;
  gpt4_equivalent_usd: number;
  human_labeler_equivalent_usd: number;
  avg_overall_confidence: number;
  cost_ratio_vs_gpt4: number | null;
  cost_ratio_vs_human: number | null;
};

export type RecentUpload = {
  id: string;
  name: string;
  files: number;
  status: "Processing" | "Completed";
  progress: number;
  iconName: string;
};

export type EvalDimension = { name: string; winRate: number };

export type ExportSample =
  | { available: true; sample: string }
  | { available: false; sample: string; hint?: string };

export type PassState = "pending" | "active" | "done" | "failed";
export type PassSummary = {
  pass: "READ" | "PROPOSE" | "CRITIQUE" | "REFINE" | "VOTE" | "ENRICH";
  state: PassState;
  ok: number;
  failed: number;
  latency_ms: number | null;
};
export type ActiveTrace =
  | { available: true; doc_id: string; filename: string; passes: PassSummary[] }
  | { available: false };

export type EvalRecordView = {
  content_type: string | null;
  summary: string;
  problem: string;
  novelty_claim: string;
  methodology_named: string[];
  methodology_freetext: string;
  domain_tags: string[];
  claim_graph: Array<Record<string, unknown>>;
};
export type EvalPair =
  | {
      available: true;
      pair_id: string;
      doc_id: string;
      filename: string;
      page_count: number | null;
      datalake: EvalRecordView;
      gpt4: EvalRecordView;
      winner: "datalake" | "gpt4" | "tie";
      judge_model: string | null;
      rationale: string | null;
      dimension_scores: Record<string, { A?: number; B?: number; a?: number; b?: number }>;
    }
  | { available: false; hint?: string };

export type FormatBar = { label: string; count: number; pct: number };

export type DocumentDetail = {
  document: {
    id: string;
    source_path: string;
    source_hash: string;
    run_id: string;
    status: string;
    content_type_guess: string | null;
    ingested_at: number;
    partial: boolean;
    timeout: boolean;
  };
  catalog: {
    content_type: string;
    content_type_confidence: number;
    ownership: string;
    ownership_confidence: number;
    ownership_rationale: string;
    compliance_flags: string[];
    commercial_score: number;
    commercial_action: string;
  } | null;
  label: {
    structured_abstract: Record<string, string>;
    methodology: { named?: string[]; other_freetext?: string | null };
    novelty_claim: string;
    evidence_quality: Record<string, unknown>;
    claim_graph: Array<Record<string, unknown>>;
    citations: Array<Record<string, unknown>>;
    domain_tags: string[];
    enriched_payload: Record<string, unknown> | null;
    partial: boolean;
  } | null;
};

async function getJSON<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(path, BASE);
  if (params) {
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  runs: () => getJSON<RunSummary[]>("/api/runs"),
  stream: (runId?: string, limit = 20) =>
    getJSON<StreamItem[]>("/api/stream", runId ? { run_id: runId, limit } : { limit }),
  catalog: (runId?: string, opts: { minScore?: number; limit?: number } = {}) =>
    getJSON<CatalogRow[]>("/api/catalog", {
      ...(runId ? { run_id: runId } : {}),
      ...(opts.minScore !== undefined ? { min_score: opts.minScore } : {}),
      ...(opts.limit !== undefined ? { limit: opts.limit } : {}),
    }),
  recentUploads: () => getJSON<RecentUpload[]>("/api/runs/recent"),
  evalDimensions: (runId?: string) =>
    getJSON<EvalDimension[]>("/api/eval/dimensions", runId ? { run_id: runId } : undefined),
  exportSample: (runId?: string) =>
    getJSON<ExportSample>("/api/export/sample", runId ? { run_id: runId } : undefined),
  counters: (runId?: string) =>
    getJSON<Counters>("/api/counters", runId ? { run_id: runId } : undefined),
  activeTrace: (runId?: string) =>
    getJSON<ActiveTrace>("/api/active-trace", runId ? { run_id: runId } : undefined),
  evalPair: (runId?: string, pairId?: string) =>
    getJSON<EvalPair>("/api/eval/pair", {
      ...(runId ? { run_id: runId } : {}),
      ...(pairId ? { pair_id: pairId } : {}),
    }),
  formatDistribution: (runId?: string) =>
    getJSON<FormatBar[]>(
      "/api/ingestion/format-distribution",
      runId ? { run_id: runId } : undefined,
    ),
  document: (docId: string) => getJSON<DocumentDetail>(`/api/document/${docId}`),
  /** Returns the direct download URL for the given export format. */
  exportDownloadUrl: (format: "jsonl" | "csv" | "card", runId?: string): string => {
    const params = new URLSearchParams({ format });
    if (runId) params.set("run_id", runId);
    return `${BASE}/api/export/download?${params.toString()}`;
  },
};
