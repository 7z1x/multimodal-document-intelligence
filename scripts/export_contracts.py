"""Export stable API and extraction contracts for clients and CI drift checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPOSITORY_ROOT / "services" / "api"
CONTRACTS_DIR = REPOSITORY_ROOT / "contracts"
sys.path.insert(0, str(API_ROOT))

from app.extraction.schemas import InvoiceData  # noqa: E402
from app.main import app  # noqa: E402


def serialized_contracts() -> dict[Path, str]:
    return {
        CONTRACTS_DIR / "openapi.json": json.dumps(
            app.openapi(), indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
        CONTRACTS_DIR / "invoice.schema.json": json.dumps(
            InvoiceData.model_json_schema(), indent=2, sort_keys=True, ensure_ascii=False
        )
        + "\n",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when committed contracts differ from the application",
    )
    args = parser.parse_args()

    stale: list[str] = []
    for path, expected in serialized_contracts().items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                stale.append(str(path.relative_to(REPOSITORY_ROOT)))
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected, encoding="utf-8", newline="\n")

    if stale:
        print("Contract drift detected: " + ", ".join(stale), file=sys.stderr)
        print("Run: pnpm contracts:export", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
