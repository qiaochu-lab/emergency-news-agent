from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from emergency_intel.config import DATA_DIR
from emergency_intel.utils import normalize_whitespace

_DEFAULT_PREFERENCES_PATH = DATA_DIR / "preferences.json"

_EMPTY_PREFERENCES: Dict[str, Any] = {
    "boost": [],
    "penalize": [],
    "preferred_sources": [],
    "few_shot_good": [],
    "few_shot_bad": [],
    "reader_notes": "",
}


def load_preferences(path: Path | None = None) -> Dict[str, Any]:
    """Load preferences.json. Returns empty defaults if file not found or malformed."""
    p = path or _DEFAULT_PREFERENCES_PATH
    if not p.exists():
        return dict(_EMPTY_PREFERENCES)
    try:
        with p.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        merged: Dict[str, Any] = dict(_EMPTY_PREFERENCES)
        merged.update({k: v for k, v in data.items() if not k.startswith("_")})
        return merged
    except Exception:
        return dict(_EMPTY_PREFERENCES)


def apply_preference_boost(text: str, final_score: float, preferences: Dict[str, Any]) -> float:
    """
    Adjust final_score based on boost/penalize keywords.
    - Each boost keyword match: +0.5 (capped at first match)
    - Each penalize keyword match: -1.0 (capped at first match)
    Score is clamped to [0.0, 10.0].
    """
    lowered = normalize_whitespace(text).lower()
    score = final_score

    for kw in preferences.get("boost", []):
        if kw.lower() in lowered:
            score += 0.5
            break

    for kw in preferences.get("penalize", []):
        if kw.lower() in lowered:
            score -= 1.0
            break

    return round(min(10.0, max(0.0, score)), 2)


def build_few_shot_prompt_block(preferences: Dict[str, Any]) -> str:
    """
    Build a prompt snippet to inject into the screening prompt.
    Returns an empty string if no examples or notes are configured.
    """
    good: List[Dict[str, str]] = preferences.get("few_shot_good", [])
    bad: List[Dict[str, str]] = preferences.get("few_shot_bad", [])
    notes: str = preferences.get("reader_notes", "").strip()

    if not good and not bad and not notes:
        return ""

    lines = ["\n读者偏好与历史反馈（请参考以下内容调整判断）："]

    if notes:
        lines.append(f"读者关注方向：{notes}")

    if good:
        lines.append("\n历史应入选示例：")
        for ex in good[:5]:
            title = ex.get("title", "")
            reason = ex.get("reason", "")
            suffix = f"（原因：{reason}）" if reason else ""
            lines.append(f"- ✅ {title}{suffix}")

    if bad:
        lines.append("\n历史不应入选示例：")
        for ex in bad[:5]:
            title = ex.get("title", "")
            reason = ex.get("reason", "")
            suffix = f"（原因：{reason}）" if reason else ""
            lines.append(f"- ❌ {title}{suffix}")

    return "\n".join(lines)
