import re
from datetime import date
from decimal import Decimal, InvalidOperation

from app.extraction.evidence import build_evidence
from app.extraction.schemas import InvoiceData, StructuredExtraction
from app.ingestion.parser import ParsedPage

AMOUNT = r"(?:IDR|USD|EUR|Rp|\$|€)?\s*([0-9][0-9.,]*)"


def parse_amount(raw: str) -> Decimal | None:
    value = re.sub(r"[^0-9.,-]", "", raw)
    if not value:
        return None
    if "," in value and "." in value:
        decimal_mark = "," if value.rfind(",") > value.rfind(".") else "."
        thousands_mark = "." if decimal_mark == "," else ","
        value = value.replace(thousands_mark, "").replace(decimal_mark, ".")
    elif "," in value:
        tail = value.rsplit(",", maxsplit=1)[-1]
        value = value.replace(",", ".") if len(tail) == 2 else value.replace(",", "")
    elif "." in value:
        tail = value.rsplit(".", maxsplit=1)[-1]
        if len(tail) != 2:
            value = value.replace(".", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_date(raw: str) -> date | None:
    parts = re.split(r"[-/]", raw.strip())
    if len(parts) != 3:
        return None
    first, second, third = (int(part) for part in parts)
    try:
        if len(parts[0]) == 4:
            return date(first, second, third)
        return date(third, second, first)
    except ValueError:
        return None


def _match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else None


class HeuristicInvoiceExtractor:
    """Transparent baseline; an LLM backend can replace it without changing the pipeline."""

    async def extract(self, pages: list[ParsedPage]) -> StructuredExtraction:
        text = "\n".join(page.text for page in pages)
        invoice_number = _match(
            r"(?:invoice\s*(?:number|no\.?|#)|nomor\s*(?:invoice|faktur))\s*[:#]?\s*([A-Z0-9][A-Z0-9./-]+)",
            text,
        )
        invoice_date_raw = _match(
            r"(?:invoice\s*date|tanggal\s*(?:invoice|faktur))\s*:?\s*([0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{2,4})",
            text,
        )
        due_date_raw = _match(
            r"(?:due\s*date|tanggal\s*jatuh\s*tempo)\s*:?\s*([0-9]{1,4}[-/][0-9]{1,2}[-/][0-9]{2,4})",
            text,
        )
        vendor_name = _match(r"(?:vendor|seller|penjual)\s*:?\s*([^\n]+)", text)
        buyer_name = _match(r"(?:buyer|bill\s*to|pembeli)\s*:?\s*([^\n]+)", text)
        subtotal_raw = _match(rf"^\s*subtotal\s*:?\s*{AMOUNT}\s*$", text)
        tax_raw = _match(rf"^\s*(?:tax|vat|ppn)(?:\s*\([^)]*\))?\s*:?\s*{AMOUNT}\s*$", text)
        total_raw = _match(
            rf"^\s*(?:grand\s*total|total\s*(?:amount|tagihan)|amount\s*due)\s*:?\s*{AMOUNT}\s*$",
            text,
        )

        currency = None
        if re.search(r"\bIDR\b|\bRp\.?\s*[0-9]", text, flags=re.IGNORECASE):
            currency = "IDR"
        elif re.search(r"\bUSD\b|\$\s*[0-9]", text, flags=re.IGNORECASE):
            currency = "USD"
        elif re.search(r"\bEUR\b|€\s*[0-9]", text, flags=re.IGNORECASE):
            currency = "EUR"

        data = InvoiceData(
            invoice_number=invoice_number,
            invoice_date=parse_date(invoice_date_raw) if invoice_date_raw else None,
            due_date=parse_date(due_date_raw) if due_date_raw else None,
            currency=currency,
            vendor_name=vendor_name,
            buyer_name=buyer_name,
            subtotal=parse_amount(subtotal_raw) if subtotal_raw else None,
            tax_amount=parse_amount(tax_raw) if tax_raw else None,
            total_amount=parse_amount(total_raw) if total_raw else None,
        )
        is_math_valid, validation_errors = data.validate_totals()
        return StructuredExtraction(
            data=data,
            evidence=build_evidence(data, pages),
            backend="heuristic",
            is_math_valid=is_math_valid,
            validation_errors=validation_errors,
        )
