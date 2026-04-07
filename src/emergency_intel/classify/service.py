from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from emergency_intel.classify.rules import DOMAIN_KEYWORDS, REGION_KEYWORDS
from emergency_intel.models import NormalizedItem
from emergency_intel.utils import normalize_whitespace, write_json


# Primary domain priority: Aviation (most specific) → AI (before Comms to prevent
# "neural network" bleeding into Communications) → Communications → DisasterTech.
# The first match becomes domain_tags[0] and determines which column an item appears in.
_DOMAIN_PRIORITY = ["Aviation", "AI", "Communications", "DisasterTech"]


def classify_items(items: Iterable[NormalizedItem], output_path: Path) -> List[NormalizedItem]:
    classified: List[NormalizedItem] = []
    for item in items:
        text = normalize_whitespace(f"{item.title} {item.raw_text}").lower()
        # Order by priority so domain_tags[0] is always the primary/column domain
        domain_tags = [
            domain for domain in _DOMAIN_PRIORITY
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
