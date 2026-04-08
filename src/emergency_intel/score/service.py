from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List

from emergency_intel.feedback.agent import apply_preference_boost, load_preferences
from emergency_intel.models import NormalizedItem, ScoredItem
from emergency_intel.score.rules import HEAT_TERMS, IMPORTANT_TERMS, SOURCE_CREDIBILITY
from emergency_intel.utils import normalize_whitespace, write_json

# Technical abbreviations that indicate substantive content
_TECH_TERMS_RE = re.compile(
    r"\b(3gpp|mcptt|mcx|mcpd|tetra|p25|ntn|haps|bvlos|utm|lte|rel\.\d+|"
    r"dbm|mhz|ghz|tbps|gbps|mbps|ipv6|ran|oran|sdr|gnss|leo|geo|meo|"
    r"etsi|itu-r|itu-t|ieee 802|c-v2x|enb|gnb)\b",
    re.IGNORECASE,
)
# Numbers with units or context (dollar amounts, percentages, coverage figures, etc.)
_DATA_RE = re.compile(
    r"(\$[\d,.]+[bmt]?|\d+[\d,.]*\s*%|\d+[\d,.]*\s*(billion|million|km|km²|states?|countries|sites?|users?|agencies?))",
    re.IGNORECASE,
)


def score_items(items: Iterable[NormalizedItem], output_path: Path) -> List[ScoredItem]:
    preferences = load_preferences()
    scored: List[ScoredItem] = []
    for item in items:
        text = normalize_whitespace(f"{item.title} {item.raw_text}").lower()
        importance = min(10.0, _score_from_terms(text, IMPORTANT_TERMS) + _domain_bonus(item.domain_tags) + _evidence_bonus(item.evidence_level))
        heat = min(10.0, _score_from_terms(text, HEAT_TERMS) + _source_heat(item.source_type))
        cred = _source_credibility(item.source_name)
        # New formula: imp×0.60 + heat×0.25 + cred×0.15 (max 10 before bonuses)
        final_score = round(importance * 0.60 + heat * 0.25 + cred * 0.15, 2)
        # Grok精选：人工筛选内容，保留加权 +1.0
        if item.source_name == "Grok精选":
            final_score = min(10.0, round(final_score + 1.0, 2))
        # Boost articles with concrete data or technical depth
        final_score = min(10.0, round(final_score + _content_quality_bonus(item.raw_text), 2))
        # Apply reader preference boost/penalize from preferences.json
        final_score = apply_preference_boost(f"{item.title} {item.raw_text}", final_score, preferences)
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


def _content_quality_bonus(raw_text: str) -> float:
    """Small bonus for articles with concrete data or technical terms.

    Signals that content has substance beyond a headline/landing page:
    - Has specific numbers/amounts/coverage figures: +0.3
    - Has technical standards abbreviations (3GPP, MCPTT, etc.): +0.2
    - Both present: +0.5 total
    - Text length > 800 chars (real article, not a snippet): +0.2
    """
    bonus = 0.0
    text = raw_text or ""
    if _DATA_RE.search(text):
        bonus += 0.3
    if _TECH_TERMS_RE.search(text):
        bonus += 0.2
    if len(text) > 800:
        bonus += 0.2
    return bonus


def _source_heat(source_type: str) -> float:
    # "social" = X/Twitter expert accounts: real-time signals, higher heat than paper/forum
    return {"news": 3.0, "official": 2.0, "social": 2.5, "company": 2.0, "paper": 1.5, "blog": 1.5}.get(source_type, 1.0)


def _source_credibility(source_name: str) -> float:
    """Return credibility score (0–10) for a source based on its domain name.

    Matches SOURCE_CREDIBILITY keys as substrings against source_name (netloc).
    Falls back to 5.0 for unknown sources.
    """
    name = (source_name or "").lower()
    for domain, score in SOURCE_CREDIBILITY.items():
        if domain in name:
            return score
    return 5.0
