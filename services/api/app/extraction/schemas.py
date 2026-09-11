from datetime import date
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class InvoiceLineItem(BaseModel):
    description: str
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_total: Decimal | None = None


class InvoiceData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    vendor_name: str | None = None
    buyer_name: str | None = None
    line_items: list[InvoiceLineItem] = Field(default_factory=list)
    subtotal: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @model_validator(mode="after")
    def dates_are_ordered(self) -> Self:
        if self.invoice_date and self.due_date and self.due_date < self.invoice_date:
            raise ValueError("due_date cannot be earlier than invoice_date")
        return self

    def validate_totals(
        self, tolerance: Decimal = Decimal("0.01")
    ) -> tuple[bool | None, list[str]]:
        if self.subtotal is None or self.tax_amount is None or self.total_amount is None:
            return None, ["subtotal, tax_amount, and total_amount are required for math validation"]
        difference = abs((self.subtotal + self.tax_amount) - self.total_amount)
        if difference <= tolerance:
            return True, []
        return False, [f"subtotal + tax_amount differs from total_amount by {difference}"]


class FieldEvidence(BaseModel):
    page_number: int = Field(ge=1)
    snippet: str


class StructuredExtraction(BaseModel):
    data: InvoiceData
    evidence: dict[str, list[FieldEvidence]] = Field(default_factory=dict)
    backend: str
    is_math_valid: bool | None
    validation_errors: list[str] = Field(default_factory=list)
