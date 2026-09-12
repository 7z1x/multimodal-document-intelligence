export type DocumentStatus =
  | "stored"
  | "processing"
  | "text_extracted"
  | "structure_extracted"
  | "indexing"
  | "indexed"
  | "failed";

export interface DocumentRecord {
  id: string;
  original_filename: string;
  media_type: string;
  size_bytes: number;
  page_count: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}

export interface InvoiceData {
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  currency: string | null;
  vendor_name: string | null;
  buyer_name: string | null;
  line_items: Array<{
    description: string;
    quantity: string | null;
    unit_price: string | null;
    line_total: string | null;
  }>;
  subtotal: string | null;
  tax_amount: string | null;
  total_amount: string | null;
}

export interface InvoiceExtraction {
  data: InvoiceData;
  evidence: Record<string, Array<{ page_number: number; snippet: string }>>;
  backend: string;
  is_math_valid: boolean | null;
  validation_errors: string[];
}

export interface IndexResult {
  document_id: string;
  chunk_count: number;
  retrieval_method: string;
}

export interface Citation {
  chunk_id: string;
  page_number: number;
  quote: string;
}

export interface AgentStep {
  node: string;
  outcome: string;
  detail: string;
  duration_ms: number;
}

export interface RetrievedChunk {
  id: string;
  document_id: string;
  page_number: number;
  chunk_index: number;
  chunk_type: "text" | "table";
  content: string;
  retrieval_score: number;
  rerank_score: number | null;
  relevance_score: number;
}

export interface RetrievalTraceItem {
  chunk_id: string;
  page_number: number;
  retrieval_score: number;
  rerank_score: number | null;
  final_relevance_score: number;
}

export interface AgentResponse {
  run_id: string | null;
  trace_id: string | null;
  document_id: string;
  question: string;
  rewritten_query: string;
  answer: string;
  citations: Citation[];
  status: "answered" | "abstained";
  is_citation_verified: boolean;
  citation_support_score: number;
  citation_errors: string[];
  attempts: number;
  latency_ms: number;
  steps: AgentStep[];
  retrieved_chunks: RetrievedChunk[];
  retrieval_trace: RetrievalTraceItem[];
  observability_status: string;
}

export interface RagRun {
  id: string;
  document_id: string;
  question: string;
  rewritten_query: string;
  answer: string;
  citations: Citation[];
  steps: AgentStep[];
  status: "answered" | "abstained";
  is_citation_verified: boolean;
  citation_support_score: number;
  citation_errors: string[];
  latency_ms: number;
  trace_id: string;
  observability_status: string;
  retrieved_chunk_ids: string[];
  retrieval_trace: RetrievalTraceItem[];
  created_at: string;
}

export interface EvaluationMetric {
  id: string;
  metric_name: string;
  score: number;
  evaluation_type: "deterministic" | "llm_as_judge";
  evaluator: string;
  threshold: number;
  passed: boolean;
  metadata: Record<string, unknown>;
}

export interface EvaluationBatch {
  batch_id: string;
  document_id: string;
  rag_run_id: string;
  overall_score: number;
  passed: boolean;
  metrics: EvaluationMetric[];
  created_at: string;
}

export interface AuditEvent {
  id: string;
  trace_id: string;
  document_id: string;
  rag_run_id: string;
  event_name: string;
  level: string;
  duration_ms: number;
  token_count: number | null;
  payload: Record<string, unknown>;
  export_status: string;
  created_at: string;
}
