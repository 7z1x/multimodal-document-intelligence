"""Deterministic, dependency-free metrics used by the local baseline benchmark."""

from __future__ import annotations


def _edit_distance(reference: list[str], prediction: list[str]) -> int:
    previous = list(range(len(prediction) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(prediction, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(reference: str, prediction: str) -> float:
    if not reference:
        return float(bool(prediction))
    return _edit_distance(list(reference), list(prediction)) / len(reference)


def word_error_rate(reference: str, prediction: str) -> float:
    reference_words = reference.split()
    prediction_words = prediction.split()
    if not reference_words:
        return float(bool(prediction_words))
    return _edit_distance(reference_words, prediction_words) / len(reference_words)


def exact_field_accuracy(expected: dict[str, str | None], actual: dict[str, str | None]) -> float:
    if not expected:
        return 0.0
    matches = sum(actual.get(field) == value for field, value in expected.items())
    return matches / len(expected)
