"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getRagRuns } from "./api";
import type { RagRun } from "./types";

export function AuditHistory({ documentId }: { documentId: string }) {
  const [runs, setRuns] = useState<RagRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getRagRuns(documentId)
      .then((result) => {
        if (active) setRuns(result);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Riwayat audit gagal dimuat");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [documentId]);

  return (
    <main className="min-h-screen bg-[#f4f1e8] px-6 py-10 text-[#17221b]">
      <div className="mx-auto max-w-4xl">
        <Link className="text-sm text-[#496451] underline underline-offset-4" href="/">
          ← Back to invoice workspace
        </Link>
        <p className="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-[#55705d]">
          Agent observability
        </p>
        <h1 className="mt-2 text-3xl font-semibold">RAG audit history</h1>
        <p className="mt-2 break-all font-mono text-xs text-[#6d776f]">{documentId}</p>

        {loading ? <p className="mt-10 text-sm text-[#6d776f]">Loading audit runs…</p> : null}
        {error ? <p className="mt-8 rounded-xl bg-[#fff0ea] p-4 text-sm text-[#8a321f]">{error}</p> : null}
        {!loading && !error && runs.length === 0 ? (
          <p className="mt-8 rounded-xl border border-[#17221b]/10 bg-white p-5 text-sm">
            No agent runs have been recorded for this document.
          </p>
        ) : null}

        <div className="mt-8 space-y-5">
          {runs.map((run) => (
            <article className="rounded-2xl border border-[#17221b]/15 bg-white p-5" key={run.id}>
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
                <span className="rounded-full bg-[#edf3ed] px-2.5 py-1 font-medium">
                  {run.status} · citations {run.is_citation_verified ? "verified" : "not verified"}
                </span>
                <time className="text-[#6d776f]" dateTime={run.created_at}>
                  {new Date(run.created_at).toLocaleString("id-ID")} · {run.latency_ms} ms
                </time>
              </div>
              <h2 className="mt-4 font-semibold">{run.question}</h2>
              <p className="mt-2 text-sm leading-6 text-[#435047]">{run.answer}</p>
              <div className="mt-4 grid gap-2 text-xs sm:grid-cols-3">
                <div className="rounded-lg bg-[#f7f5ef] p-3">
                  Citation support: {(run.citation_support_score * 100).toFixed(0)}%
                </div>
                <div className="rounded-lg bg-[#f7f5ef] p-3">
                  Retrieved: {run.retrieval_trace.length}
                </div>
                <div className="rounded-lg bg-[#f7f5ef] p-3">
                  Reranked: {run.retrieval_trace.filter((item) => item.rerank_score !== null).length}
                </div>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#6d776f]">
                    Rewritten query
                  </p>
                  <p className="mt-2 rounded-lg bg-[#f7f5ef] p-3 text-xs leading-5">
                    {run.rewritten_query}
                  </p>
                  <p className="mt-2 text-[11px] text-[#6d776f]">
                    Retrieved chunks: {run.retrieved_chunk_ids.length}
                  </p>
                  {run.citation_errors.length ? (
                    <p className="mt-2 text-[11px] text-[#9a3e2d]">
                      Verification: {run.citation_errors.join(", ")}
                    </p>
                  ) : null}
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#6d776f]">
                    Node trace
                  </p>
                  <ol className="mt-2 space-y-1 text-xs">
                    {run.steps.map((step, index) => (
                      <li className="flex justify-between rounded-md bg-[#f7f5ef] px-3 py-2" key={`${run.id}-${index}`}>
                        <span title={step.detail}>{index + 1}. {step.node}</span>
                        <span className="text-[#55705d]">{step.outcome}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </main>
  );
}
