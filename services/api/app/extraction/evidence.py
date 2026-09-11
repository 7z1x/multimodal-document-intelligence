from datetime import date
from decimal import Decimal

from app.extraction.schemas import FieldEvidence, InvoiceData
from app.ingestion.parser import ParsedPage


def _variants(value: object) -> list[str]:
    if isinstance(value, Decimal):
        plain = format(value, "f")
        integer, _, fraction = plain.partition(".")
        grouped_id = f"{int(integer):,}".replace(",", ".")
        grouped_us = f"{int(integer):,}"
        variants = [plain, plain.replace(".", ",")]
        if fraction:
            variants.extend([f"{grouped_id},{fraction}", f"{grouped_us}.{fraction}"])
        if not fraction or set(fraction) == {"0"}:
            variants.extend([integer, grouped_id, grouped_us])
        return variants
    if isinstance(value, date):
        return [value.isoformat(), value.strftime("%d/%m/%Y"), value.strftime("%d-%m-%Y")]
    return [str(value)]


def build_evidence(data: InvoiceData, pages: list[ParsedPage]) -> dict[str, list[FieldEvidence]]:
    evidence: dict[str, list[FieldEvidence]] = {}
    fields = {
        "invoice_number": data.invoice_number,
        "invoice_date": data.invoice_date,
        "due_date": data.due_date,
        "vendor_name": data.vendor_name,
        "buyer_name": data.buyer_name,
        "subtotal": data.subtotal,
        "tax_amount": data.tax_amount,
        "total_amount": data.total_amount,
    }

    for field_name, value in fields.items():
        if value is None:
            continue
        needles = [variant.casefold() for variant in _variants(value)]
        for page in pages:
            for line in page.text.splitlines():
                if any(needle in line.casefold() for needle in needles):
                    evidence.setdefault(field_name, []).append(
                        FieldEvidence(page_number=page.page_number, snippet=line.strip()[:500])
                    )
                    break
            if field_name in evidence:
                break
    return evidence
