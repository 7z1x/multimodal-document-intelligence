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
}

export interface RetrievedChunk {
  id: string;
  document_id: string;
  page_number: number;
  chunk_index: number;
  chunk_type: "text" | "table";
  content: string;
  relevance_score: number;
}

export interface AgentResponse {
  run_id: string | null;
  document_id: string;
  question: string;
  rewritten_query: string;
  answer: string;
  citations: Citation[];
  status: "answered" | "abstained";
  is_citation_verified: boolean;
  attempts: number;
  latency_ms: number;
  steps: AgentStep[];
  retrieved_chunks: RetrievedChunk[];
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
  latency_ms: number;
  retrieved_chunk_ids: string[];
  created_at: string;
}
