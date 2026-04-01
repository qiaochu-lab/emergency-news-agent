from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set, Tuple

from emergency_intel.models import NormalizedItem
from emergency_intel.utils import write_json


def deduplicate_items(items: Iterable[NormalizedItem], output_path: Path) -> Tuple[List[NormalizedItem], int]:
    deduped: List[NormalizedItem] = []
    seen_urls: Set[str] = set()
    seen_titles: Set[str] = set()
    seen_fingerprints: Set[str] = set()
    removed = 0

    for item in items:
        if item.canonical_url in seen_urls or item.normalized_title in seen_titles or item.content_fingerprint in seen_fingerprints:
            removed += 1
            continue
        deduped.append(item)
        seen_urls.add(item.canonical_url)
        seen_titles.add(item.normalized_title)
        seen_fingerprints.add(item.content_fingerprint)

    write_json(output_path, [entry.__dict__ for entry in deduped])
    return deduped, removed
