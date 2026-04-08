"""
Review feedback consumer.

Two sources of feedback:
1. YYYY-WXX-review.md files annotated with [wrong] / [should] markers.
2. GitHub Issues created by the HTML report's 感兴趣/不太感冒 buttons.

Both sources update preferences.json which is read by the next pipeline run.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Tuple

from emergency_intel.config import DATA_DIR

# GitHub repo and token for reading feedback issues
_GITHUB_REPO  = "qiaochu-lab/emergency-news-agent"
_GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

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


# ──────────────────────────────────────────────
# GitHub Issues feedback
# ──────────────────────────────────────────────

def consume_github_feedback(
    preferences_path: Path | None = None,
    repo: str = _GITHUB_REPO,
    token: str = _GITHUB_TOKEN,
) -> str:
    """
    Fetch open GitHub Issues with label 'feedback', parse interested/not_interested,
    update preferences.json, then close each processed issue.
    Returns a short summary string.
    """
    prefs_path = preferences_path or _PREFERENCES_PATH

    try:
        issues = _fetch_feedback_issues(repo, token)
    except Exception as e:
        return f"[GitHub反馈] 获取失败：{e}"

    if not issues:
        return "[GitHub反馈] 暂无新反馈"

    good: List[Dict] = []
    bad: List[Dict] = []
    processed_numbers: List[int] = []

    for issue in issues:
        title = issue.get("title", "")
        body  = issue.get("body", "")
        number = issue.get("number")

        # Parse item_id from body: "**条目ID**: some-id"
        item_id_m = re.search(r"\*\*条目ID\*\*:\s*(.+)", body)
        item_id = item_id_m.group(1).strip() if item_id_m else title

        labels = [lb["name"] for lb in issue.get("labels", [])]
        entry = {"title": item_id, "reason": "来自周报页面点击反馈"}

        if "interested" in labels:
            good.append(entry)
        elif "not_interested" in labels:
            bad.append(entry)
        else:
            continue  # skip unrecognised labels

        processed_numbers.append(number)

    if not processed_numbers:
        return "[GitHub反馈] 暂无可解析的反馈"

    _update_preferences(prefs_path, few_shot_bad=bad, few_shot_good=good)

    # Close processed issues
    for num in processed_numbers:
        try:
            _close_issue(repo, token, num)
        except Exception:
            pass

    return (
        f"[GitHub反馈] 处理 {len(processed_numbers)} 条：{len(good)} 感兴趣，{len(bad)} 不感兴趣，"
        f"已写入 preferences.json"
    )


def _fetch_feedback_issues(repo: str, token: str) -> List[Dict]:
    """GET /repos/{repo}/issues?labels=feedback&state=open"""
    url = f"https://api.github.com/repos/{repo}/issues?labels=feedback&state=open&per_page=100"
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def _close_issue(repo: str, token: str, issue_number: int) -> None:
    """PATCH /repos/{repo}/issues/{number} with state=closed"""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    data = json.dumps({"state": "closed"}).encode()
    req = urllib.request.Request(url, data=data, method="PATCH", headers={
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v3+json",
    })
    urllib.request.urlopen(req, timeout=10)
