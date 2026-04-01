from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable


def append_weekly_run_log(
    log_path: Path,
    *,
    source_registry_path: Path,
    items_collected: int,
    items_screened_in: int,
    items_selected: int,
    duplicates_removed: int,
    report_path: Path,
    collection_errors: Iterable[str],
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    errors = list(collection_errors)
    error_text = "；".join(errors[:5]) if errors else "无"
    entry = [
        f"## {timestamp}",
        "",
        f"- Source registry: `{source_registry_path}`",
        f"- Collected items: `{items_collected}`",
        f"- Screened in: `{items_screened_in}`",
        f"- Selected for report: `{items_selected}`",
        f"- Duplicates removed: `{duplicates_removed}`",
        f"- Report path: `{report_path}`",
        f"- Failed sources / errors: {error_text}",
        "- Analyst notes: ",
        "",
    ]
    prefix = ""
    if log_path.exists() and log_path.read_text(encoding="utf-8").strip():
        prefix = "\n"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(prefix + "\n".join(entry) + "\n")
