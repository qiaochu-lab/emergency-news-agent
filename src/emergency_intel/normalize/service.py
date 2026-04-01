from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from emergency_intel.models import NormalizedItem, RawItem
from emergency_intel.utils import (
    canonicalize_url,
    fingerprint_text,
    normalize_title,
    normalize_whitespace,
    write_json,
)


SOURCE_TYPE_TO_EVIDENCE = {
    "official": "Official",
    "paper": "Academic",
    "news": "Industry media",
    "company": "Industry media",
    "social": "Industry media",
    "blog": "Industry media",
    "forum": "Industry media",
}

SOURCE_TYPE_TO_CONTENT = {
    "official": "Announcement",
    "paper": "Paper",
    "news": "News",
    "company": "News",
    "social": "Social",
    "blog": "Blog",
}


def normalize_items(items: Iterable[RawItem], output_path: Path) -> List[NormalizedItem]:
    normalized: List[NormalizedItem] = []
    for item in items:
        normalized.append(
            NormalizedItem(
                **item.to_dict(),
                content_type=SOURCE_TYPE_TO_CONTENT.get(item.source_type, "News"),
                evidence_level=SOURCE_TYPE_TO_EVIDENCE.get(item.source_type, "Secondary mention"),
                normalized_title=normalize_title(item.title),
                canonical_url=canonicalize_url(item.url),
                content_fingerprint=fingerprint_text(normalize_whitespace(item.raw_text)),
            )
        )
    write_json(output_path, [entry.__dict__ for entry in normalized])
    return normalized
