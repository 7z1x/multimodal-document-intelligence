import re

from app.generation.schemas import GeneratedAnswer
from app.retrieval.schemas import RetrievedChunk


def normalize_evidence(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def verify_citations(answer: GeneratedAnswer, contexts: list[RetrievedChunk]) -> bool:
    if not answer.can_answer or not answer.citations:
        return False
    chunks = {chunk.id: chunk for chunk in contexts}
    for citation in answer.citations:
        chunk = chunks.get(citation.chunk_id)
        if chunk is None or chunk.page_number != citation.page_number:
            return False
        quote = normalize_evidence(citation.quote)
        if not quote or quote not in normalize_evidence(chunk.content):
            return False
    return True
