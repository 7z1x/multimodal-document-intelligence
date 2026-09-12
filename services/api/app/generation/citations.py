import re

from app.generation.schemas import CitationVerification, GeneratedAnswer
from app.retrieval.schemas import RetrievedChunk


def normalize_evidence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def verify_citations(answer: GeneratedAnswer, contexts: list[RetrievedChunk]) -> bool:
    return verify_citation_support(answer, contexts).valid


def verify_citation_support(
    answer: GeneratedAnswer,
    contexts: list[RetrievedChunk],
) -> CitationVerification:
    errors: list[str] = []
    total = len(answer.citations)
    supported = 0
    if not answer.can_answer:
        errors.append("model_declined_to_answer")
    if total == 0:
        errors.append("answer_has_no_citations")
    chunks = {chunk.id: chunk for chunk in contexts}
    for index, citation in enumerate(answer.citations):
        chunk = chunks.get(citation.chunk_id)
        if chunk is None:
            errors.append(f"citation_{index}:chunk_not_retrieved")
            continue
        if chunk.page_number != citation.page_number:
            errors.append(f"citation_{index}:page_mismatch")
            continue
        quote = normalize_evidence(citation.quote)
        if not quote or quote not in normalize_evidence(chunk.content):
            errors.append(f"citation_{index}:quote_not_found")
            continue
        supported += 1
    score = supported / total if total else 0.0
    return CitationVerification(
        valid=answer.can_answer and total > 0 and not errors,
        total_citations=total,
        supported_citations=supported,
        support_score=score,
        errors=errors,
    )
