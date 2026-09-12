def id_context_precision(retrieved_ids: list[str], reference_ids: set[str]) -> float:
    """Average precision over ranked IDs, equivalent to ID-based context precision."""
    if not retrieved_ids or not reference_ids:
        return 0.0
    relevant_seen = 0
    precision_sum = 0.0
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in reference_ids:
            relevant_seen += 1
            precision_sum += relevant_seen / rank
    return precision_sum / len(reference_ids)


def hit_at_k(retrieved_ids: list[str], reference_ids: set[str], k: int) -> float:
    return float(any(chunk_id in reference_ids for chunk_id in retrieved_ids[:k]))


def abstention_correctness(status: str, expected_answerable: bool) -> float:
    did_answer = status == "answered"
    return float(did_answer is expected_answerable)
