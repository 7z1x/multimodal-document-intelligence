# PaddleOCR Clean-Scan Baseline

Source run: [GitHub Actions 34704232528](https://github.com/7z1x/multimodal-document-intelligence/actions/runs/34704232528)

- Generated: `2026-09-12T16:07:49.958706+00:00`
- Engine: `PaddleOCR PP-StructureV3`
- Dataset: `invoice_native_001` (1 synthetic clean scan)
- CER: `0.0000` (gate `<= 0.05`)
- WER: `0.0000` (gate `<= 0.08`)
- Mean confidence: `0.9781`
- Cold-run duration including model initialization: `58.001 s`
- Status: **PASS**

Reference and normalized prediction were identical. The complete machine-readable result is retained as the `paddleocr-baseline` artifact on the source run.

## Scope limitation

This is a regression smoke test on one clean synthetic scan. It does not measure noisy scans, rotated real-world captures, varied production layouts, p95 latency, or a production-sized dataset. The workflow is manual so PaddleOCR runs in GitHub Actions rather than consuming the developer laptop.
