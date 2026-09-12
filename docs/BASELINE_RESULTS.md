# Baseline Results

Generated: `2026-09-12T16:06:34.755978+00:00`

Status: **PASS**

Dataset: `invoice_native_001` (1 document, 3 queries)

Retrieval: `postgresql-full-text`

| Metric | Result | Gate |
|---|---:|---:|
| `native_parse_success` | 1.0000 | 1.0000 |
| `field_exact_accuracy` | 1.0000 | 0.9500 |
| `math_validation_success` | 1.0000 | 1.0000 |
| `mean_hit_at_1` | 1.0000 | 1.0000 |
| `mean_hit_at_3` | 1.0000 | 1.0000 |
| `mean_hit_at_5` | 1.0000 | 1.0000 |
| `mean_context_precision` | 1.0000 | 0.8500 |
| `citation_page_accuracy` | 1.0000 | 0.9500 |
| `mean_citation_support` | 1.0000 | 1.0000 |

## Scope limitations

- This is a one-document synthetic regression baseline, not a production benchmark.
- PaddleOCR CER/WER is not measured because local model execution is intentionally disabled.
- CER/WER metric implementations are covered by deterministic unit tests only.
