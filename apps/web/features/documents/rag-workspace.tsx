"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { askDocument, indexDocument } from "./api";
import type { AgentResponse, IndexResult } from "./types";

interface RagWorkspaceProps {
  documentId: string;
}

export function RagWorkspace({ documentId }: RagWorkspaceProps) {
  const [indexResult, setIndexResult] = useState<IndexResult | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AgentResponse | null>(null);
  const [busy, setBusy] = useState<"index" | "ask" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function buildIndex() {
    setBusy("index");
    setError(null);
    try {
      setIndexResult(await indexDocument(documentId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Indeks RAG gagal dibuat");
    } finally {
      setBusy(null);
    }
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuestion = question.trim();
    if (!normalizedQuestion) return;
    setBusy("ask");
    setError(null);
    try {
      setAnswer(await askDocument(documentId, normalizedQuestion));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Agent gagal menjawab");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="mt-4 rounded-xl border border-[#17221b]/15 bg-[#17221b] p-4 text-[#f7f3e8]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#a9c2af]">
            Stage 8–9
          </p>
          <h4 className="mt-1 font-semibold">Grounded agentic RAG</h4>
        </div>
        {indexResult ? (
          <span className="rounded-full bg-[#315b3e] px-2.5 py-1 text-[11px]">
            {indexResult.chunk_count} chunks indexed
          </span>
        ) : null}
      </div>

      {!indexResult ? (
        <button
          className="mt-4 w-full rounded-lg bg-[#f1e5c8] px-4 py-2.5 text-sm font-semibold text-[#183f2a] transition hover:bg-white disabled:cursor-wait disabled:opacity-60"
          disabled={busy !== null}
          onClick={buildIndex}
          type="button"
        >
          {busy === "index" ? "Indexing document…" : "Build RAG index"}
        </button>
      ) : (
        <form className="mt-4" onSubmit={ask}>
          <label className="text-xs text-[#c8d4ca]" htmlFor="rag-question">
            Ask only about this invoice
          </label>
          <textarea
            className="mt-2 min-h-24 w-full resize-y rounded-lg border border-white/15 bg-white/10 px-3 py-2.5 text-sm text-white outline-none placeholder:text-white/35 focus:border-[#d7c08a]"
            id="rag-question"
            maxLength={2000}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Example: When is this invoice due and what is the total?"
            value={question}
          />
          <button
            className="mt-2 w-full rounded-lg bg-[#b65a36] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#cc6841] disabled:cursor-wait disabled:opacity-60"
            disabled={busy !== null || question.trim().length < 2}
            type="submit"
          >
            {busy === "ask" ? "Agent is verifying evidence…" : "Ask verified agent"}
          </button>
        </form>
      )}

      {error ? (
        <p className="mt-3 rounded-lg bg-[#7f3028]/70 px-3 py-2 text-xs" role="alert">
          {error}
        </p>
      ) : null}

      {answer ? (
        <div className="mt-4 space-y-4 border-t border-white/15 pt-4">
          <div className="flex items-center justify-between gap-3 text-xs">
            <span
              className={`rounded-full px-2.5 py-1 ${
                answer.status === "answered" ? "bg-[#315b3e]" : "bg-[#745443]"
              }`}
            >
              {answer.status}
            </span>
            <span className="text-white/55">
              {answer.attempts} attempt · {answer.latency_ms} ms
            </span>
          </div>
          <p className="text-sm leading-6 text-[#fffaf0]">{answer.answer}</p>

          {answer.citations.length ? (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#a9c2af]">
                Verified citations
              </p>
              {answer.citations.map((citation) => (
                <blockquote
                  className="rounded-lg border-l-2 border-[#d7c08a] bg-white/5 px-3 py-2 text-xs leading-5 text-white/75"
                  key={`${citation.chunk_id}-${citation.quote}`}
                >
                  Page {citation.page_number}: “{citation.quote}”
                </blockquote>
              ))}
            </div>
          ) : null}

          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-[#a9c2af]">
              Agent audit trail
            </p>
            <ol className="mt-2 space-y-1.5">
              {answer.steps.map((step, index) => (
                <li
                  className="grid grid-cols-[20px_1fr_auto] gap-2 rounded-md bg-white/5 px-2.5 py-2 text-[11px]"
                  key={`${step.node}-${index}`}
                >
                  <span className="text-white/40">{index + 1}</span>
                  <span>{step.node}</span>
                  <span className="text-[#b9cebd]">{step.outcome}</span>
                </li>
              ))}
            </ol>
          </div>

          <details className="rounded-lg bg-white/5 px-3 py-2 text-xs">
            <summary className="cursor-pointer text-white/70">
              Retrieved context ({answer.retrieved_chunks.length})
            </summary>
            <div className="mt-3 space-y-3">
              {answer.retrieved_chunks.map((chunk) => (
                <div className="border-t border-white/10 pt-2" key={chunk.id}>
                  <p className="text-white/45">
                    Page {chunk.page_number} · relevance {chunk.relevance_score.toFixed(3)}
                  </p>
                  <p className="mt-1 line-clamp-4 leading-5 text-white/70">{chunk.content}</p>
                </div>
              ))}
            </div>
          </details>

          {answer.run_id ? (
            <Link
              className="inline-flex text-xs font-medium text-[#e2cd98] underline underline-offset-4"
              href={`/audit/${documentId}`}
            >
              Open complete audit history →
            </Link>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
