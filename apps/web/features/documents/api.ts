import type { ApiErrorPayload, DocumentRecord, InvoiceExtraction } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_URL}/api/v1/documents`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new Error(payload.error?.message ?? "Dokumen gagal diunggah");
  }

  return (await response.json()) as DocumentRecord;
}

export async function processDocument(documentId: string): Promise<InvoiceExtraction> {
  const response = await fetch(`${API_URL}/api/v1/documents/${documentId}/process`, {
    method: "POST",
  });

  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
    throw new Error(payload.error?.message ?? "Dokumen gagal dianalisis");
  }

  return (await response.json()) as InvoiceExtraction;
}
