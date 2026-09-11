export type DocumentStatus = "stored" | "processing" | "failed";

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
