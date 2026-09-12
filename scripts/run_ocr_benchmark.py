"""Run the real PaddleOCR adapter on a rendered synthetic scan."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pypdfium2 as pdfium

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPOSITORY_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

from app.evaluation.benchmark_metrics import character_error_rate, word_error_rate  # noqa: E402
from app.ocr.paddle import PaddleStructureEngine  # noqa: E402


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def render_first_page(path: Path) -> object:
    document = pdfium.PdfDocument(path)
    page = document[0]
    # A clean 96-DPI scan keeps the full PP-StructureV3 pipeline inside a
    # standard GitHub-hosted runner's memory while preserving readable text.
    bitmap = page.render(scale=96 / 72)
    try:
        return bitmap.to_pil().convert("RGB")
    finally:
        bitmap.close()
        page.close()
        document.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    truth_path = REPOSITORY_ROOT / "datasets" / "ground-truth" / "invoice_native_001.json"
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    sample = REPOSITORY_ROOT / "datasets" / "samples" / truth["filename"]
    image = render_first_page(sample)

    started = time.perf_counter()
    result = PaddleStructureEngine().recognize(image)  # type: ignore[arg-type]
    duration = round((time.perf_counter() - started) * 1_000, 2)
    reference = normalize(truth["ocr_reference_text"])
    prediction = normalize(result.text)
    metrics = {
        "cer_scan_clean": character_error_rate(reference, prediction),
        "wer_scan_clean": word_error_rate(reference, prediction),
    }
    thresholds = {"cer_scan_clean": 0.05, "wer_scan_clean": 0.08}
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": truth["id"],
        "engine": "PaddleOCR PP-StructureV3",
        "sample_count": 1,
        "metrics": metrics,
        "thresholds": thresholds,
        "passed": all(metrics[key] <= threshold for key, threshold in thresholds.items()),
        "duration_ms": duration,
        "mean_confidence": result.confidence,
        "reference": reference,
        "prediction": prediction,
        "limitation": (
            "One clean synthetic scan; noisy scans and production layouts remain unmeasured."
        ),
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    print(serialized)
    if args.report:
        target = args.report if args.report.is_absolute() else REPOSITORY_ROOT / args.report
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding="utf-8", newline="\n")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
