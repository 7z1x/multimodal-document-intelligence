import json
from math import ceil
from typing import Any, Literal

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.documents.page_models import DocumentPage
from app.retrieval.schemas import ChunkDraft


class PageAwareChunker:
    def __init__(self, *, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
        )

    def split(self, pages: list[DocumentPage]) -> list[ChunkDraft]:
        drafts: list[ChunkDraft] = []
        for page in sorted(pages, key=lambda item: item.page_number):
            for content in self.splitter.split_text(page.text.strip()):
                self._append(drafts, page.page_number, "text", content)
            for table in self._tables(page.layout_json):
                for content in self.splitter.split_text(table):
                    self._append(drafts, page.page_number, "table", content)
        return drafts

    @staticmethod
    def _tables(layout: dict[str, object]) -> list[str]:
        raw_tables = layout.get("tables", [])
        if not isinstance(raw_tables, list):
            return []
        return [PageAwareChunker._table_text(table) for table in raw_tables if table]

    @staticmethod
    def _table_text(table: Any) -> str:
        if isinstance(table, dict):
            for key in ("pred_html", "html", "table_ocr_pred", "markdown", "text"):
                value = table.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return json.dumps(table, ensure_ascii=False, sort_keys=True, default=str)

    @staticmethod
    def _append(
        drafts: list[ChunkDraft],
        page_number: int,
        chunk_type: Literal["text", "table"],
        content: str,
    ) -> None:
        normalized = content.strip()
        if not normalized:
            return
        drafts.append(
            ChunkDraft(
                page_number=page_number,
                chunk_index=len(drafts),
                chunk_type=chunk_type,
                content=normalized,
                token_count=max(1, ceil(len(normalized) / 4)),
            )
        )
