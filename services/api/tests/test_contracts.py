import json
from pathlib import Path

from app.extraction.schemas import InvoiceData
from app.main import app

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_openapi_contract_is_current() -> None:
    committed = json.loads((REPOSITORY_ROOT / "contracts" / "openapi.json").read_text())
    assert committed == app.openapi()


def test_invoice_schema_contract_is_current() -> None:
    committed = json.loads(
        (REPOSITORY_ROOT / "contracts" / "invoice.schema.json").read_text()
    )
    assert committed == InvoiceData.model_json_schema()
