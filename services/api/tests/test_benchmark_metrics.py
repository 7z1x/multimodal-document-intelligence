import pytest

from app.evaluation.benchmark_metrics import (
    character_error_rate,
    exact_field_accuracy,
    word_error_rate,
)


def test_ocr_error_metrics_have_known_values() -> None:
    assert character_error_rate("invoice", "invo1ce") == pytest.approx(1 / 7)
    assert word_error_rate("grand total invoice", "grand invoice") == pytest.approx(1 / 3)
    assert character_error_rate("", "") == 0


def test_exact_field_accuracy_counts_missing_and_wrong_values() -> None:
    expected = {"invoice_number": "INV-001", "currency": "IDR", "total_amount": "110000"}
    actual = {"invoice_number": "INV-001", "currency": "IDR", "total_amount": None}

    assert exact_field_accuracy(expected, actual) == pytest.approx(2 / 3)
