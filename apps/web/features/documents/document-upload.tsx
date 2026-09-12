"use client";

import { ChangeEvent, DragEvent, useRef, useState } from "react";

import { processDocument, uploadDocument } from "./api";
import type { DocumentRecord, InvoiceExtraction } from "./types";
import { RagWorkspace } from "./rag-workspace";

const MAX_BYTES = 15 * 1024 * 1024;
const ACCEPTED_TYPES = ["application/pdf", "image/jpeg", "image/png"];

function readableSize(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export function DocumentUpload() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [document, setDocument] = useState<DocumentRecord | null>(null);
  const [extraction, setExtraction] = useState<InvoiceExtraction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  function selectFile(candidate?: File) {
    setDocument(null);
    setExtraction(null);
    setError(null);
    if (!candidate) return;
    if (!ACCEPTED_TYPES.includes(candidate.type)) {
      setFile(null);
      setError("Pilih berkas PDF, JPG, atau PNG.");
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setFile(null);
      setError("Ukuran berkas melebihi batas 15 MB.");
      return;
    }
    setFile(candidate);
  }

  function onInputChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    selectFile(event.dataTransfer.files?.[0]);
  }

  async function submit() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      setDocument(await uploadDocument(file));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Dokumen gagal diunggah");
    } finally {
      setUploading(false);
    }
  }

  async function analyze() {
    if (!document) return;
    setUploading(true);
    setError(null);
    try {
      setExtraction(await processDocument(document.id));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Dokumen gagal dianalisis");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="rounded-[28px] border border-[#17221b]/15 bg-[#fffdf8] p-5 shadow-[0_24px_70px_rgba(45,55,47,0.12)] md:p-7">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#55705d]">
            Secure intake
          </p>
          <h3 className="mt-2 text-xl font-semibold">Upload an invoice</h3>
        </div>
        <span className="rounded-md bg-[#edf3ed] px-2 py-1 font-mono text-[11px] text-[#365540]">
          MAX 10 PAGES
        </span>
      </div>

      <div
        className="mt-6 flex min-h-56 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-[#55705d]/45 bg-[#f6f7f0] px-6 text-center transition hover:border-[#b0512d]/70 hover:bg-[#faf7ef]"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={onDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") inputRef.current?.click();
        }}
      >
        <span className="grid h-12 w-12 place-items-center rounded-full bg-[#e3ebe3] text-2xl text-[#365540]">
          ↑
        </span>
        <p className="mt-4 font-medium">Drop an invoice here</p>
        <p className="mt-1 text-sm text-[#6d776f]">PDF, JPG, or PNG · up to 15 MB</p>
        <input
          ref={inputRef}
          className="sr-only"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          onChange={onInputChange}
        />
      </div>

      {file ? (
        <div className="mt-4 flex items-center justify-between gap-4 rounded-xl border border-[#17221b]/10 px-4 py-3 text-sm">
          <div className="min-w-0">
            <p className="truncate font-medium">{file.name}</p>
            <p className="text-xs text-[#6d776f]">{readableSize(file.size)}</p>
          </div>
          <button
            className="rounded-lg bg-[#183f2a] px-4 py-2 font-medium text-white transition hover:bg-[#285c3d] disabled:cursor-wait disabled:opacity-60"
            disabled={uploading}
            onClick={submit}
            type="button"
          >
            {uploading ? "Validating…" : "Upload"}
          </button>
        </div>
      ) : null}

      {error ? (
        <p className="mt-4 rounded-xl bg-[#fff0ea] px-4 py-3 text-sm text-[#8a321f]" role="alert">
          {error}
        </p>
      ) : null}

      {document ? (
        <div className="mt-4 rounded-xl border border-[#4a7658]/25 bg-[#edf5ee] px-4 py-4 text-sm">
          <div className="flex items-center justify-between gap-4">
            <p className="font-semibold text-[#244d31]">Document stored safely</p>
            <span className="rounded-full bg-white px-2 py-1 text-[11px] uppercase tracking-wide text-[#365540]">
              {document.status}
            </span>
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-xs text-[#516456]">
            <div><dt>Pages</dt><dd className="mt-1 font-medium text-[#17221b]">{document.page_count}</dd></div>
            <div><dt>Size</dt><dd className="mt-1 font-medium text-[#17221b]">{readableSize(document.size_bytes)}</dd></div>
          </dl>
          {!extraction ? (
            <button
              className="mt-4 w-full rounded-lg border border-[#244d31]/20 bg-white px-4 py-2.5 font-medium text-[#244d31] transition hover:bg-[#f7fbf7] disabled:cursor-wait disabled:opacity-60"
              disabled={uploading}
              onClick={analyze}
              type="button"
            >
              {uploading ? "Analyzing…" : "Extract invoice fields"}
            </button>
          ) : null}
        </div>
      ) : null}

      {extraction ? (
        <div className="mt-4 rounded-xl border border-[#17221b]/15 bg-white px-4 py-4 text-sm">
          <div className="flex items-center justify-between gap-3">
            <p className="font-semibold">Structured extraction</p>
            <span className="rounded-full bg-[#f1eee5] px-2 py-1 text-[11px] uppercase tracking-wide">
              {extraction.backend}
            </span>
          </div>
          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
            {[
              ["Invoice", extraction.data.invoice_number],
              ["Vendor", extraction.data.vendor_name],
              ["Date", extraction.data.invoice_date],
              ["Due date", extraction.data.due_date],
              ["Currency", extraction.data.currency],
              ["Total", extraction.data.total_amount],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[#748078]">{label}</dt>
                <dd className="mt-1 break-words font-medium text-[#17221b]">{value ?? "Not found"}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 border-t border-[#17221b]/10 pt-3 text-xs text-[#5f6b63]">
            Math check: {extraction.is_math_valid === null ? "insufficient fields" : extraction.is_math_valid ? "valid" : "needs review"}
          </p>
        </div>
      ) : null}

      {extraction && document ? <RagWorkspace documentId={document.id} /> : null}
    </section>
  );
}
