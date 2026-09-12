import type {
  AgentResponse,
  ApiErrorPayload,
  DocumentRecord,
  IndexResult,
  InvoiceExtraction,
  RagRun,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new Error(payload.error?.message ?? fallback);
  }
  return (await response.json()) as T;
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_URL}/api/v1/documents`, {
    method: "POST",
    body,
  });

  return parseResponse<DocumentRecord>(response, "Dokumen gagal diunggah");
}

export async function processDocument(documentId: string): Promise<InvoiceExtraction> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/process`, {
    method: "POST",
  });

  return parseResponse<InvoiceExtraction>(response, "Dokumen gagal dianalisis");
}

export async function indexDocument(documentId: string): Promise<IndexResult> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/index`, {
    method: "POST",
  });
  return parseResponse<IndexResult>(response, "Indeks RAG gagal dibuat");
}

export async function askDocument(documentId: string, question: string): Promise<AgentResponse> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return parseResponse<AgentResponse>(response, "Agent gagal menjawab pertanyaan");
}

export async function getRagRuns(documentId: string): Promise<RagRun[]> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/rag-runs`, {
    cache: "no-store",
  });
  return parseResponse<RagRun[]>(response, "Riwayat audit gagal dimuat");
}
