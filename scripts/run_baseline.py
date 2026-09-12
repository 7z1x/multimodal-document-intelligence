"""Run the checked-in synthetic benchmark against real application components."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPOSITORY_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from app.core.config import get_settings  # noqa: E402
from app.documents.models import Document, DocumentStatus  # noqa: E402
from app.documents.page_models import DocumentPage  # noqa: E402
from app.evaluation.benchmark_metrics import exact_field_accuracy  # noqa: E402
from app.evaluation.metrics import hit_at_k, id_context_precision  # noqa: E402
from app.extraction.heuristic import HeuristicInvoiceExtractor  # noqa: E402
from app.generation.citations import verify_citation_support  # noqa: E402
from app.generation.schemas import Citation, GeneratedAnswer  # noqa: E402
from app.ingestion.parser import DocumentParser  # noqa: E402
from app.retrieval.chunking import PageAwareChunker  # noqa: E402
from app.retrieval.models import DocumentChunk  # noqa: E402
from app.retrieval.repository import PostgresTextChunkRepository  # noqa: E402


def _normalize_fields(data: Any) -> dict[str, str | None]:
    raw = data.model_dump()
    fields: dict[str, str | None] = {}
    for key, value in raw.items():
        if key == "line_items":
            continue
        fields[key] = None if value is None else str(value)
    return fields


async def run() -> dict[str, Any]:
    truth_path = REPOSITORY_ROOT / "datasets" / "ground-truth" / "invoice_native_001.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    sample_path = REPOSITORY_ROOT / "datasets" / "samples" / truth["filename"]
    if not sample_path.exists():
        raise RuntimeError("Synthetic sample missing. Run: pnpm dataset:generate")

    started = time.perf_counter()
    pages = await DocumentParser(ocr_engine=None, native_min_characters=40).parse(
        sample_path, truth["media_type"]
    )
    extraction = await HeuristicInvoiceExtractor().extract(pages)
    field_accuracy = exact_field_accuracy(
        truth["expected_fields"], _normalize_fields(extraction.data)
    )

    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    query_results: list[dict[str, Any]] = []
    document_id = uuid.uuid4()
    try:
        async with factory() as session:
            document = Document(
                id=document_id,
                original_filename=truth["filename"],
                stored_filename=f"benchmark-{document_id}.pdf",
                media_type=truth["media_type"],
                size_bytes=sample_path.stat().st_size,
                page_count=len(pages),
                sha256="0" * 64,
                status=DocumentStatus.INDEXED,
            )
            session.add(document)
            await session.flush()
            persisted_pages = [
                DocumentPage(
                    document_id=document_id,
                    page_number=page.page_number,
                    extraction_method=page.extraction_method,
                    text=page.text,
                    character_count=page.character_count,
                    layout_json=page.layout,
                )
                for page in pages
            ]
            session.add_all(persisted_pages)
            await session.flush()
            drafts = PageAwareChunker(chunk_size=180, chunk_overlap=20).split(persisted_pages)
            repository = PostgresTextChunkRepository(session)
            await repository.replace(document_id, drafts)
            await session.flush()
            stored_chunks = list(
                (
                    await session.scalars(
                        select(DocumentChunk).where(DocumentChunk.document_id == document_id)
                    )
                ).all()
            )

            for query in truth["queries"]:
                retrieved = await repository.search(document_id, query["question"], 5)
                references = {
                    str(chunk.id)
                    for chunk in stored_chunks
                    if query["reference_text"] in chunk.content
                }
                if not references:
                    raise RuntimeError(f"No reference chunk for query: {query['question']}")
                ranked_ids = [str(chunk.id) for chunk in retrieved]
                top = retrieved[0] if retrieved else None
                citation_score = 0.0
                citation_valid = False
                if top is not None:
                    answer = GeneratedAnswer(
                        can_answer=True,
                        answer=query["reference_text"],
                        citations=[
                            Citation(
                                chunk_id=top.id,
                                page_number=top.page_number,
                                quote=query["reference_text"],
                            )
                        ],
                    )
                    verification = verify_citation_support(answer, retrieved)
                    citation_score = verification.support_score
                    citation_valid = verification.valid
                query_results.append(
                    {
                        "question": query["question"],
                        "hit_at_1": hit_at_k(ranked_ids, references, 1),
                        "hit_at_3": hit_at_k(ranked_ids, references, 3),
                        "hit_at_5": hit_at_k(ranked_ids, references, 5),
                        "context_precision": id_context_precision(ranked_ids, references),
                        "citation_page_accuracy": float(citation_valid),
                        "citation_support": citation_score,
                    }
                )

            await session.execute(delete(Document).where(Document.id == document_id))
            await session.commit()
    finally:
        await engine.dispose()

    def mean(key: str) -> float:
        return sum(item[key] for item in query_results) / len(query_results)

    metrics = {
        "native_parse_success": float(
            all(page.extraction_method == truth["expected_extraction_method"] for page in pages)
        ),
        "field_exact_accuracy": field_accuracy,
        "math_validation_success": float(extraction.is_math_valid is True),
        "mean_hit_at_1": mean("hit_at_1"),
        "mean_hit_at_3": mean("hit_at_3"),
        "mean_hit_at_5": mean("hit_at_5"),
        "mean_context_precision": mean("context_precision"),
        "citation_page_accuracy": mean("citation_page_accuracy"),
        "mean_citation_support": mean("citation_support"),
    }
    thresholds = {
        "native_parse_success": 1.0,
        "field_exact_accuracy": 0.95,
        "math_validation_success": 1.0,
        "mean_hit_at_1": 1.0,
        "mean_hit_at_3": 1.0,
        "mean_hit_at_5": 1.0,
        "mean_context_precision": 0.85,
        "citation_page_accuracy": 0.95,
        "mean_citation_support": 1.0,
    }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": "invoice_native_001",
        "sample_count": 1,
        "query_count": len(query_results),
        "retrieval_backend": "postgresql-full-text",
        "metrics": metrics,
        "thresholds": thresholds,
        "passed": all(metrics[key] >= threshold for key, threshold in thresholds.items()),
        "duration_ms": round((time.perf_counter() - started) * 1_000, 2),
        "queries": query_results,
        "limitations": [
            "This is a one-document synthetic regression baseline, not a production benchmark.",
            (
                "PaddleOCR CER/WER is not measured because local model execution "
                "is intentionally disabled."
            ),
            "CER/WER metric implementations are covered by deterministic unit tests only.",
        ],
    }


def markdown(result: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| `{name}` | {value:.4f} | {result['thresholds'][name]:.4f} |"
        for name, value in result["metrics"].items()
    )
    limitations = "\n".join(f"- {item}" for item in result["limitations"])
    status = "PASS" if result["passed"] else "FAIL"
    return f"""# Baseline Results

Generated: `{result['generated_at']}`

Status: **{status}**

Dataset: `{result['dataset']}` \
({result['sample_count']} document, {result['query_count']} queries)

Retrieval: `{result['retrieval_backend']}`

| Metric | Result | Gate |
|---|---:|---:|
{rows}

## Scope limitations

{limitations}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run())
    print(json.dumps(result, indent=2))
    if args.report:
        target = args.report if args.report.is_absolute() else REPOSITORY_ROOT / args.report
        target.write_text(markdown(result), encoding="utf-8", newline="\n")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
