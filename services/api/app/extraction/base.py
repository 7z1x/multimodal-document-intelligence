from typing import Protocol

from app.extraction.schemas import StructuredExtraction
from app.ingestion.parser import ParsedPage


class InvoiceExtractor(Protocol):
    async def extract(self, pages: list[ParsedPage]) -> StructuredExtraction: ...
