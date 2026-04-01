from __future__ import annotations

from typing import Dict

from emergency_intel.models import RawItem
from emergency_intel.utils import normalize_whitespace


LANDING_PAGE_TERMS = (
    "about us",
    "overview",
    "categories",
    "directory",
    "work with us",
    "community",
    "newsletter",
    "subscribe",
)


def audit_raw_item(item: RawItem) -> Dict[str, object]:
    text = normalize_whitespace(item.raw_text)
    lowered = f"{item.title} {text} {item.url}".lower()
    text_length = len(text)
    likely_landing_page = any(term in lowered for term in LANDING_PAGE_TERMS) or _nav_density(text)
    if likely_landing_page:
        quality = "landing_page_or_noise"
    elif text_length < 220:
        quality = "short_summary"
    elif text_length < 1200:
        quality = "article_summary"
    else:
        quality = "full_body_candidate"

    return {
        "source_name": item.source_name,
        "title": item.title,
        "url": item.url,
        "text_length": text_length,
        "quality_label": quality,
        "likely_landing_page": likely_landing_page,
        "preview": text[:220],
    }


def _nav_density(text: str) -> bool:
    lowered = text.lower()
    nav_hits = sum(
        1
        for term in ("sign in", "log in", "cookie", "privacy", "terms", "menu", "search", "subscribe")
        if term in lowered
    )
    return nav_hits >= 3 and len(text) < 1800
