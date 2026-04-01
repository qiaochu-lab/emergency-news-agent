"""Parse weekly manual input files (data/manual/YYYY-WXX-*.md) into RawItem objects.

File naming convention: YYYY-WXX-[domain].md  e.g. 2026-W14-AI.md
Each file covers one domain's Grok-sourced content for one ISO week.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from emergency_intel.models import RawItem
from emergency_intel.utils import normalize_whitespace, slugify


_SOURCE_NAME = "Grok精选"
_SOURCE_TYPE = "social"


def load_manual_items(manual_dir: Path, iso_week: str | None = None) -> List[RawItem]:
    """Load all manual input files for the given ISO week (e.g. '2026-W14').

    If iso_week is None, defaults to the current week.
    Returns an empty list if the directory doesn't exist or no files match.
    """
    if not manual_dir.exists():
        return []

    if iso_week is None:
        now = datetime.now(tz=timezone.utc)
        year, week, _ = now.isocalendar()
        iso_week = f"{year}-W{week:02d}"

    items: List[RawItem] = []
    pattern = f"{iso_week}-*.md"

    for path in sorted(manual_dir.glob(pattern)):
        if path.name == "template.md":
            continue
        items.extend(_parse_manual_file(path))

    if items:
        print(f"[手动输入] 加载 {iso_week} 共 {len(items)} 条（{len(list(manual_dir.glob(pattern)))} 个文件）", flush=True)

    return items


def _parse_manual_file(path: Path) -> List[RawItem]:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = _split_frontmatter(text)
    domain = frontmatter.get("domain", "AI")
    date_range = frontmatter.get("date_range", "")
    published_at = _parse_date_range_end(date_range)

    entries = _split_entries(body)
    items: List[RawItem] = []

    for entry in entries:
        title = entry.get("title", "").strip()
        summary = entry.get("summary", "").strip()
        why = entry.get("why_notable", "").strip()
        url = entry.get("url", "").strip()
        author = entry.get("author", "").strip()

        # Skip incomplete entries
        if not title or title in ("标题（必填）",) or not summary:
            continue

        raw_text = normalize_whitespace(f"{summary} {why}")
        item_id = slugify(f"manual-{title[:40]}")

        items.append(RawItem(
            id=item_id,
            source_type=_SOURCE_TYPE,
            source_name=_SOURCE_NAME,
            title=title,
            url=url or "",
            published_at=published_at,
            language="zh",
            raw_text=raw_text,
            content_depth="summary",
            body_extraction_status=f"manual:{author}" if author else "manual",
        ))

    return items


def _split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML-like frontmatter between --- delimiters."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    fm_text, body = match.group(1), match.group(2)
    frontmatter: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            frontmatter[key.strip()] = val.strip()

    return frontmatter, body


def _split_entries(body: str) -> List[dict[str, str]]:
    """Split body into entry blocks by ## N headers."""
    blocks = re.split(r"^##\s+\d+\s*$", body, flags=re.MULTILINE)
    entries: List[dict[str, str]] = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        entry: dict[str, str] = {}
        for line in block.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                k = key.strip().lower()
                v = val.strip()
                if k in ("title", "author", "url", "summary", "why_notable") and v:
                    entry[k] = v
        if entry:
            entries.append(entry)

    return entries


def _parse_date_range_end(date_range: str) -> str:
    """Extract end date from 'YYYY-MM-DD ~ YYYY-MM-DD' and return ISO format."""
    match = re.search(r"(\d{4}-\d{2}-\d{2})\s*$", date_range.strip())
    if match:
        return match.group(1) + "T00:00:00+00:00"
    return datetime.now(tz=timezone.utc).isoformat()
