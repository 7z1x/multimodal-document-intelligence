from typing import Protocol

from PIL import Image

from app.ocr.schemas import OcrPageResult


class OcrEngine(Protocol):
    def recognize(self, image: Image.Image) -> OcrPageResult: ...
