"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { evaluateRagRun, getEvaluations, getRagRuns, getTraceEvents } from "./api";
import type { AuditEvent, EvaluationBatch, RagRun } from "./types";

export function AuditHistory({ documentId }: { documentId: string }) {
  const [runs, setRuns] = useState<RagRun[]>([]);
  const [evaluations, setEvaluations] = useState<EvaluationBatch[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [references, setReferences] = useState<Record<string, string>>({});
  const [evaluating, setEvaluating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([getRagRuns(documentId), getEvaluations(documentId), getTraceEvents(documentId)])
      .then(([runResult, evaluationResult, eventResult]) => {
        if (!active) return;
        setRuns(runResult);
        setEvaluations(evaluationResult);
        setEvents(eventResult);
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Audit data gagal dimuat");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [documentId]);

  async function evaluate(runId: string) {
    setEvaluating(runId);
    setError(null);
    try {
      const result = await evaluateRagRun(documentId, runId, references[runId]);
      setEvaluations((current) => [result, ...current]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Evaluasi RAG gagal dijalankan");
    } finally {
      setEvaluating(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#f4f1e8] px-6 py-10 text-[#17221b]">
      <div className="mx-auto max-w-5xl">
        <Link className="text-sm text-[#496451] underline underline-offset-4" href="/">
          ← Back to invoice workspace
        </Link>
        <p className="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-[#55705d]">
          Stage 13–14 · Evaluation & observability
        </p>
        <h1 className="mt-2 text-3xl font-semibold">RAG quality and trace audit</h1>
        <p className="mt-2 break-all font-mono text-xs text-[#6d776f]">{documentId}</p>

        <div className="mt-6 grid gap-3 text-sm sm:grid-cols-3">
          <div className="rounded-xl border border-[#17221b]/10 bg-white p-4">
            <p className="text-[#6d776f]">Agent runs</p>
            <p className="mt-1 text-2xl font-semibold">{runs.length}</p>
          </div>
          <div className="rounded-xl border border-[#17221b]/10 bg-white p-4">
            <p className="text-[#6d776f]">Evaluation batches</p>
            <p className="mt-1 text-2xl font-semibold">{evaluations.length}</p>
          </div>
          <div className="rounded-xl border border-[#17221b]/10 bg-white p-4">
            <p className="text-[#6d776f]">Structured trace events</p>
            <p className="mt-1 text-2xl font-semibold">{events.length}</p>
          </div>
        </div>

        {loading ? <p className="mt-10 text-sm text-[#6d776f]">Loading audit data…</p> : null}
        {error ? <p className="mt-8 rounded-xl bg-[#fff0ea] p-4 text-sm text-[#8a321f]">{error}</p> : null}
        {!loading && !error && runs.length === 0 ? (
          <p className="mt-8 rounded-xl border border-[#17221b]/10 bg-white p-5 text-sm">
            No agent runs have been recorded for this document.
          </p>
        ) : null}

        <div className="mt-8 space-y-5">
          {runs.map((run) => {
            const evaluation = evaluations.find((item) => item.rag_run_id === run.id);
            return (
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
                <div className="mt-4 grid gap-2 text-xs sm:grid-cols-4">
                  <MetricCard label="Citation support" value={`${(run.citation_support_score * 100).toFixed(0)}%`} />
                  <MetricCard label="Retrieved" value={String(run.retrieval_trace.length)} />
                  <MetricCard
                    label="Reranked"
                    value={String(run.retrieval_trace.filter((item) => item.rerank_score !== null).length)}
                  />
                  <MetricCard label="Trace export" value={run.observability_status} />
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[#6d776f]">Rewritten query</p>
                    <p className="mt-2 rounded-lg bg-[#f7f5ef] p-3 text-xs leading-5">{run.rewritten_query}</p>
                    <p className="mt-2 break-all font-mono text-[11px] text-[#6d776f]">Trace: {run.trace_id}</p>
                    {run.citation_errors.length ? (
                      <p className="mt-2 text-[11px] text-[#9a3e2d]">Verification: {run.citation_errors.join(", ")}</p>
                    ) : null}
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[#6d776f]">Node trace</p>
                    <ol className="mt-2 space-y-1 text-xs">
                      {run.steps.map((step, index) => (
                        <li className="flex justify-between rounded-md bg-[#f7f5ef] px-3 py-2" key={`${run.id}-${index}`}>
                          <span title={step.detail}>{index + 1}. {step.node}</span>
                          <span className="text-[#55705d]">{step.outcome} · {step.duration_ms} ms</span>
                        </li>
                      ))}
                    </ol>
                  </div>
                </div>

                <section className="mt-5 rounded-xl border border-[#17221b]/10 bg-[#faf8f2] p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-[#6d776f]">Evaluation sample</p>
                      <p className="mt-1 text-xs text-[#6d776f]">Reference answer is optional; add it to enable answer-correctness.</p>
                    </div>
                    <button
                      className="rounded-lg bg-[#183f2a] px-3 py-2 text-xs font-semibold text-white disabled:cursor-wait disabled:opacity-60"
                      disabled={evaluating !== null || run.status !== "answered"}
                      onClick={() => evaluate(run.id)}
                      type="button"
                    >
                      {evaluating === run.id ? "Evaluating with Muse…" : "Evaluate this run"}
                    </button>
                  </div>
                  <input
                    className="mt-3 w-full rounded-lg border border-[#17221b]/15 bg-white px-3 py-2 text-xs outline-none focus:border-[#55705d]"
                    maxLength={4000}
                    onChange={(event) => setReferences((current) => ({ ...current, [run.id]: event.target.value }))}
                    placeholder="Optional ground-truth answer"
                    value={references[run.id] ?? ""}
                  />
                  {evaluation ? (
                    <div className="mt-4">
                      <p className={`text-sm font-semibold ${evaluation.passed ? "text-[#315b3e]" : "text-[#9a3e2d]"}`}>
                        Overall {(evaluation.overall_score * 100).toFixed(0)}% · {evaluation.passed ? "passed" : "needs review"}
                      </p>
                      <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                        {evaluation.metrics.map((metric) => (
                          <div className="rounded-lg bg-white p-3 text-xs" key={metric.id}>
                            <div className="flex justify-between gap-2">
                              <span>{metric.metric_name.replaceAll("_", " ")}</span>
                              <span className={metric.passed ? "text-[#315b3e]" : "text-[#9a3e2d]"}>
                                {(metric.score * 100).toFixed(0)}%
                              </span>
                            </div>
                            <p className="mt-1 text-[10px] text-[#7a827c]">{metric.evaluation_type} · target {(metric.threshold * 100).toFixed(0)}%</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </section>
              </article>
            );
          })}
        </div>

        {events.length ? (
          <section className="mt-10">
            <h2 className="text-xl font-semibold">Structured audit events</h2>
            <div className="mt-4 space-y-2">
              {events.map((event) => (
                <div className="grid gap-2 rounded-xl border border-[#17221b]/10 bg-white p-4 text-xs sm:grid-cols-[1fr_auto]" key={event.id}>
                  <div>
                    <p className="font-semibold">{event.event_name}</p>
                    <p className="mt-1 break-all font-mono text-[10px] text-[#6d776f]">{event.trace_id}</p>
                  </div>
                  <p className="text-[#6d776f]">{event.duration_ms} ms · tokens {event.token_count ?? "not reported"} · {event.export_status}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-[#f7f5ef] p-3">
      <p className="text-[#6d776f]">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
