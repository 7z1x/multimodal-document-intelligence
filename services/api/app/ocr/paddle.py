from collections.abc import Mapping, Sequence
from importlib import import_module
from statistics import fmean
from typing import Any

from PIL import Image

from app.core.exceptions import AppError
from app.ocr.schemas import OcrBlock, OcrPageResult


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_jsonable(item) for item in value]
    if hasattr(value, "tolist"):
        return _jsonable(value.tolist())
    return str(value)


class PaddleStructureEngine:
    """Lazy PP-StructureV3 adapter so non-OCR API paths stay lightweight."""

    def __init__(self) -> None:
        try:
            np = import_module("numpy")
            PPStructureV3 = import_module("paddleocr").PPStructureV3
        except ImportError as exc:
            raise AppError(
                code="OCR_DEPENDENCY_UNAVAILABLE",
                message="PaddleOCR belum terpasang; install backend dengan extra 'ocr'",
                status_code=503,
            ) from exc

        self._numpy = np
        self._pipeline = PPStructureV3(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True,
            use_formula_recognition=False,
            use_chart_recognition=False,
            use_seal_recognition=False,
            enable_mkldnn=False,
        )

    def recognize(self, image: Image.Image) -> OcrPageResult:
        outputs = list(self._pipeline.predict(self._numpy.asarray(image.convert("RGB"))))
        if not outputs:
            raise AppError(code="OCR_EMPTY_RESULT", message="PaddleOCR tidak menghasilkan output")

        raw_json = outputs[0].json
        payload = raw_json() if callable(raw_json) else raw_json
        safe_payload = _jsonable(payload)
        if not isinstance(safe_payload, dict):
            raise AppError(code="OCR_INVALID_RESULT", message="Format output PaddleOCR tidak valid")

        result = safe_payload.get("res", safe_payload)
        if not isinstance(result, dict):
            result = safe_payload
        overall = result.get("overall_ocr_res", {})
        if not isinstance(overall, dict):
            overall = {}

        texts = overall.get("rec_texts", [])
        scores = overall.get("rec_scores", [])
        polygons = overall.get("rec_polys", overall.get("dt_polys", []))
        if not isinstance(texts, list):
            texts = []
        if not isinstance(scores, list):
            scores = []
        if not isinstance(polygons, list):
            polygons = []

        blocks: list[OcrBlock] = []
        for index, value in enumerate(texts):
            text = str(value).strip()
            if not text:
                continue
            confidence = float(scores[index]) if index < len(scores) else None
            polygon = polygons[index] if index < len(polygons) else []
            blocks.append(OcrBlock(text=text, confidence=confidence, polygon=polygon))

        numeric_scores = [block.confidence for block in blocks if block.confidence is not None]
        confidence = fmean(numeric_scores) if numeric_scores else None
        layout = {
            "layout_detection": result.get("layout_det_res", {}),
            "tables": result.get("table_res_list", []),
        }
        return OcrPageResult(
            text="\n".join(block.text for block in blocks),
            confidence=confidence,
            blocks=blocks,
            layout=_jsonable(layout),
        )


class LazyPaddleStructureEngine:
    def __init__(self) -> None:
        self._engine: PaddleStructureEngine | None = None

    def recognize(self, image: Image.Image) -> OcrPageResult:
        if self._engine is None:
            self._engine = PaddleStructureEngine()
        return self._engine.recognize(image)
