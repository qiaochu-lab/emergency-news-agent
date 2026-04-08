from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from hashlib import sha1
from pathlib import Path
from typing import Iterable, List, Sequence, TypeVar
from urllib.parse import urlparse, urlunparse


T = TypeVar("T")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def read_json(path: Path, default: object) -> object:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_title(title: str) -> str:
    cleaned = normalize_whitespace(title).lower()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff ]+", "", cleaned)


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    stripped = parsed._replace(query="", fragment="")
    return urlunparse(stripped)


def fingerprint_text(text: str) -> str:
    normalized = normalize_whitespace(text).lower()
    return sha1(normalized[:2000].encode("utf-8")).hexdigest()


def week_window(reference: date | None = None) -> tuple[date, date]:
    """Return (start, end) of the report week: the ISO Mon–Sun prior to reference date."""
    today = reference or date.today()
    start = today - timedelta(days=today.weekday() + 7)
    return start, start + timedelta(days=6)


def week_range_label(reference: date | None = None) -> str:
    start, end = week_window(reference)
    return f"{start.isoformat()} to {end.isoformat()}"


def chunked(sequence: Sequence[T], size: int) -> Iterable[List[T]]:
    for idx in range(0, len(sequence), size):
        yield list(sequence[idx : idx + size])


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
