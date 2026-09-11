from dataclasses import dataclass, field


@dataclass(frozen=True)
class OcrBlock:
    text: str
    confidence: float | None = None
    polygon: list[list[float]] = field(default_factory=list)


@dataclass(frozen=True)
class OcrPageResult:
    text: str
    confidence: float | None
    blocks: list[OcrBlock] = field(default_factory=list)
    layout: dict[str, object] = field(default_factory=dict)
