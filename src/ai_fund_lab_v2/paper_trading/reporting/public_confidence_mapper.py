from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class PublicConfidence:
    public_confidence_score: int
    public_confidence_label: str
    short_reason: str
    caution_note: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def public_confidence_label(score: int) -> str:
    if score >= 90:
        return "非常に強い"
    if score >= 75:
        return "強い"
    if score >= 60:
        return "やや強い"
    if score >= 40:
        return "中立"
    if score >= 25:
        return "弱い"
    return "見送り"


def map_public_confidence(
    *,
    internal_score: float | int | None = None,
    risk_penalty: float | int | None = None,
    safety_status: str = "OK",
    short_reason: str = "",
    caution_note: str = "",
) -> PublicConfidence:
    score = _normalize_score(internal_score)
    score -= int(round(max(_to_float(risk_penalty), 0.0) * 20))
    if str(safety_status or "").upper() not in {"OK", "READY_FOR_REVIEW", "UNLOCKED"}:
        score = min(score, 40)
    score = max(0, min(100, score))
    return PublicConfidence(
        public_confidence_score=score,
        public_confidence_label=public_confidence_label(score),
        short_reason=short_reason or "公開用に丸めた説明スコアです。",
        caution_note=caution_note or "勝率、将来上昇確率、期待利益率ではありません。",
    )


def map_candidate_public_confidence(candidate: Mapping[str, Any], *, safety_status: str = "OK") -> PublicConfidence:
    if candidate.get("public_confidence_score") not in (None, ""):
        score = max(0, min(100, int(candidate["public_confidence_score"])))
        return PublicConfidence(
            public_confidence_score=score,
            public_confidence_label=str(candidate.get("public_confidence_label") or public_confidence_label(score)),
            short_reason=str(candidate.get("short_reason") or "公開用に丸めた説明スコアです。"),
            caution_note=str(candidate.get("caution_note") or "勝率、将来上昇確率、期待利益率ではありません。"),
        )
    return map_public_confidence(
        internal_score=candidate.get("score") or candidate.get("confidence") or candidate.get("opportunity_score"),
        risk_penalty=candidate.get("risk_penalty") or candidate.get("risk_score"),
        safety_status=safety_status,
        short_reason=str(candidate.get("short_reason") or candidate.get("reason") or ""),
        caution_note=str(candidate.get("caution_note") or ""),
    )


def _normalize_score(value: float | int | None) -> int:
    numeric = _to_float(value)
    if 0.0 <= numeric <= 1.0:
        return int(round(numeric * 100))
    return int(round(numeric))


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 50.0

