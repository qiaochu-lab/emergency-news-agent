from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from emergency_intel.classify.rules import DOMAIN_KEYWORDS, REGION_KEYWORDS
from emergency_intel.models import NormalizedItem
from emergency_intel.utils import normalize_whitespace, write_json


# Primary domain priority: Aviation (most specific) → AI → Communications → DisasterTech.
# Title-based overrides: if the title contains strong comms or aviation signals, that domain
# is promoted to primary regardless of body text matches.
_DOMAIN_PRIORITY = ["Aviation", "AI", "Communications", "DisasterTech"]

# Title keywords that force Communications to primary (even if aviation body text matches)
_COMMS_TITLE_KEYWORDS = [
    "5g", "6g", "private 5g", "private network", "satellite", "leo satellite",
    "leo network", "spectrum", "ran", "ntn", "satcom", "backhaul",
    "firstnet", "esn", "direct-to-satellite", "ngso", "gso",
    "deployable comms", "over-the-air computation", "connectivity solution",
    "authentication scheme", "digital twin edge", "iot",
]

# Title keywords that keep Aviation as primary
_AVIATION_TITLE_KEYWORDS = [
    "drone", "uav", "uas", "bvlos", "unmanned", "autopilot", "px4",
    "counter drone", "counter-uas", "counter uas",
]


def _priority_for_title(title: str) -> list:
    t = title.lower()
    if any(kw in t for kw in _AVIATION_TITLE_KEYWORDS):
        return ["Aviation", "Communications", "AI", "DisasterTech"]
    if any(kw in t for kw in _COMMS_TITLE_KEYWORDS):
        return ["Communications", "Aviation", "AI", "DisasterTech"]
    return _DOMAIN_PRIORITY


def classify_items(items: Iterable[NormalizedItem], output_path: Path) -> List[NormalizedItem]:
    classified: List[NormalizedItem] = []
    for item in items:
        text = normalize_whitespace(f"{item.title} {item.raw_text}").lower()
        priority = _priority_for_title(item.title)
        # Order by priority so domain_tags[0] is always the primary/column domain
        domain_tags = [
            domain for domain in priority
            if any(keyword in text for keyword in DOMAIN_KEYWORDS[domain])
        ]
        region_tags = [region for region, keywords in REGION_KEYWORDS.items() if any(keyword in text for keyword in keywords)]

        if not domain_tags:
            domain_tags = ["AI"] if item.source_type == "social" else ["DisasterTech"]

        item.domain_tags = domain_tags
        item.region_tags = region_tags or ["Global"]
        item.entity_tags = _extract_entities(text)
        classified.append(item)

    write_json(output_path, [entry.__dict__ for entry in classified])
    return classified


def _extract_entities(text: str) -> List[str]:
    candidates = ["OpenAI", "NVIDIA", "FCC", "FEMA", "NASA", "ITU", "NIST", "arXiv"]
    return [name for name in candidates if name.lower() in text]
