from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from emergency_intel.models import NormalizedItem, ScoredItem
from emergency_intel.score.rules import HEAT_TERMS, IMPORTANT_TERMS
from emergency_intel.utils import normalize_whitespace, write_json


def score_items(items: Iterable[NormalizedItem], output_path: Path) -> List[ScoredItem]:
    scored: List[ScoredItem] = []
    for item in items:
        text = normalize_whitespace(f"{item.title} {item.raw_text}").lower()
        importance = min(10.0, _score_from_terms(text, IMPORTANT_TERMS) + _domain_bonus(item.domain_tags) + _evidence_bonus(item.evidence_level))
        heat = min(10.0, _score_from_terms(text, HEAT_TERMS) + _source_heat(item.source_type))
        final_score = round(importance * 0.7 + heat * 0.3, 2)
        # Boost curated feeds from known high-quality sources
        if item.source_name in ("follow-builders X Feed",):
            final_score = min(10.0, round(final_score + 1.5, 2))
        # Grok精选：人工筛选内容，加权 +1.0
        if item.source_name == "Grok精选":
            final_score = min(10.0, round(final_score + 1.0, 2))
        scored.append(
            ScoredItem(
                **item.__dict__,
                importance_score=round(importance, 2),
                heat_score=round(heat, 2),
                final_score=final_score,
            )
        )

    scored.sort(key=lambda entry: entry.final_score, reverse=True)
    write_json(output_path, [entry.__dict__ for entry in scored])
    return scored


def _score_from_terms(text: str, rules: dict[int, list[str]]) -> float:
    score = 0.0
    for weight, keywords in rules.items():
        if any(keyword in text for keyword in keywords):
            score += weight
    return score


def _domain_bonus(tags: List[str]) -> float:
    return 1.5 if len(tags) > 1 else 1.0


def _evidence_bonus(level: str) -> float:
    if level == "Official":
        return 3.0
    if level == "Academic":
        return 2.0
    if level == "Industry media":
        return 1.0
    return 0.5


def _source_heat(source_type: str) -> float:
    # "social" = X/Twitter expert accounts: real-time signals, higher heat than paper/forum
    return {"news": 3.0, "official": 2.0, "social": 2.5, "company": 2.0, "paper": 1.5, "blog": 1.5}.get(source_type, 1.0)
