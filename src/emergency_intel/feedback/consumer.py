"""
Review feedback consumer.

Reads YYYY-WXX-review.md files that humans have annotated, extracts
[wrong] / [should] markers, and updates preferences.json so the next
pipeline run benefits from those signals.

Consumed files are renamed to YYYY-WXX-review.done.md to avoid
double-processing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from emergency_intel.config import DATA_DIR

_PREFERENCES_PATH = DATA_DIR / "preferences.json"
_FEEDBACK_DIR = DATA_DIR / "feedback"

# Max few-shot examples kept in preferences (oldest dropped when exceeded)
_MAX_FEW_SHOT = 20

# Regex: "- [MARK] score | title | domain | source"
_ITEM_RE = re.compile(
    r"^-\s+\[(?P<mark>\w+)\]\s+(?P<score>[\d.]+)\s*\|\s*(?P<title>[^|]+)\|(?P<rest>.+)$"
)


def consume_pending_reviews(
    feedback_dir: Path | None = None,
    preferences_path: Path | None = None,
) -> str:
    """
    Find all unprocessed review files, parse annotations, update preferences.json.
    Returns a short summary string for logging.
    """
    fb_dir = feedback_dir or _FEEDBACK_DIR
    prefs_path = preferences_path or _PREFERENCES_PATH

    review_files = sorted(fb_dir.glob("*-review.md"))
    if not review_files:
        return "无待处理反馈文件"

    total_wrong = total_should = 0
    processed = []

    for path in review_files:
        wrong, should = _parse_review_file(path)
        if not wrong and not should:
            # No annotations — still mark consumed so we don't re-scan each run
            _mark_consumed(path)
            processed.append(path.name)
            continue

        _update_preferences(prefs_path, few_shot_bad=wrong, few_shot_good=should)
        _mark_consumed(path)
        total_wrong += len(wrong)
        total_should += len(should)
        processed.append(path.name)

    if not processed:
        return "无待处理反馈文件"

    return (
        f"[反馈] 处理 {len(processed)} 份反馈：{total_wrong} 条不该入选，{total_should} 条应入选，"
        f"已写入 preferences.json"
    )


def _parse_review_file(path: Path) -> Tuple[List[Dict], List[Dict]]:
    """
    Parse a review.md file.
    Returns (wrong_items, should_items) as lists of {title, reason} dicts.
    """
    wrong: List[Dict] = []
    should: List[Dict] = []

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return wrong, should

    for line in text.splitlines():
        m = _ITEM_RE.match(line.strip())
        if not m:
            continue
        mark = m.group("mark").lower()
        if mark not in ("wrong", "should"):
            continue

        title = m.group("title").strip()
        rest = m.group("rest").strip()
        # rest = "domain | source_name" or just "domain"
        parts = [p.strip() for p in rest.split("|")]
        domain = parts[0] if parts else ""
        source = parts[1] if len(parts) > 1 else ""
        reason = f"领域：{domain}；来源：{source}" if source else f"领域：{domain}"

        entry = {"title": title, "reason": reason}
        if mark == "wrong":
            wrong.append(entry)
        else:
            should.append(entry)

    return wrong, should


def _update_preferences(
    prefs_path: Path,
    few_shot_bad: List[Dict],
    few_shot_good: List[Dict],
) -> None:
    """Merge new examples into preferences.json, dedup by title, keep latest."""
    prefs: Dict = {}
    if prefs_path.exists():
        try:
            prefs = json.loads(prefs_path.read_text(encoding="utf-8"))
        except Exception:
            prefs = {}

    def _merge(existing: List[Dict], new_items: List[Dict]) -> List[Dict]:
        seen_titles = {e["title"] for e in existing}
        merged = list(existing)
        for item in new_items:
            if item["title"] not in seen_titles:
                merged.append(item)
                seen_titles.add(item["title"])
        # Keep most recent _MAX_FEW_SHOT entries
        return merged[-_MAX_FEW_SHOT:]

    prefs["few_shot_bad"] = _merge(prefs.get("few_shot_bad", []), few_shot_bad)
    prefs["few_shot_good"] = _merge(prefs.get("few_shot_good", []), few_shot_good)

    prefs_path.write_text(
        json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _mark_consumed(path: Path) -> None:
    """Rename review.md → review.done.md to prevent reprocessing."""
    done_path = path.with_name(path.name.replace("-review.md", "-review.done.md"))
    try:
        path.rename(done_path)
    except Exception:
        pass
