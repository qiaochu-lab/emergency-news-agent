"""Media source adapter: YouTube channels, podcast RSS feeds, and manual URL input.

Flow per episode:
  URL → yt-dlp download (audio only, mp3) → Groq Whisper transcription → LLM summarization → RawItem
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Optional, Tuple

from emergency_intel.models import RawItem
from emergency_intel.utils import ensure_dir, utc_now_iso

_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_MAX_EPISODES_PER_SOURCE = 2   # Cap per source per weekly run
_MIN_TRANSCRIPT_CHARS = 200


def collect_media_items(
    source_registry: list,
    groq_api_key: str,
    youtube_api_key: str,
    provider,
    manual_dir: Optional[Path] = None,
    reference_date: Optional[date] = None,
) -> List[RawItem]:
    """
    Collect, transcribe, and summarize media items.
    Returns empty list if groq_api_key is blank.
    """
    if not groq_api_key:
        return []

    from emergency_intel.transcribe.service import transcribe_audio_file
    from emergency_intel.transcribe.summarizer import summarize_transcript

    ref = reference_date or date.today()
    cutoff = datetime(ref.year, ref.month, ref.day, tzinfo=timezone.utc) - timedelta(days=7)
    items: List[RawItem] = []

    media_sources = [
        s for s in source_registry
        if s.get("enabled") and s.get("access_method") in ("youtube", "podcast_rss")
    ]

    for source in media_sources:
        method = source.get("access_method")
        name = source.get("name", "unknown")
        try:
            if method == "youtube":
                if not youtube_api_key:
                    print(f"[媒体] 跳过 {name}：未配置 EI_YOUTUBE_API_KEY", flush=True)
                    continue
                episodes = _get_recent_youtube_videos(source["url"], youtube_api_key, cutoff)
            else:
                episodes = _get_recent_podcast_episodes(source["url"], cutoff)

            for url, pub_date in episodes[:_MAX_EPISODES_PER_SOURCE]:
                item = _process_url(
                    url, name, pub_date,
                    groq_api_key, provider,
                    transcribe_audio_file, summarize_transcript,
                )
                if item:
                    items.append(item)

        except Exception as exc:
            print(f"[媒体] ✗ {name}: {exc}", flush=True)

    # Manual URL input: data/media/YYYY-WXX-urls.txt
    if manual_dir:
        for item in _load_manual_urls(
            manual_dir, ref, groq_api_key, provider,
            transcribe_audio_file, summarize_transcript,
        ):
            items.append(item)

    if items:
        print(f"[媒体转录] 完成：共 {len(items)} 条", flush=True)

    return items


# ── YouTube ──────────────────────────────────────────────────────────────────

def _get_recent_youtube_videos(
    channel_id: str,
    api_key: str,
    cutoff: datetime,
) -> List[Tuple[str, str]]:
    """Return [(video_url, published_at_iso)] for videos published after cutoff."""
    published_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")
    params = (
        f"?part=snippet&channelId={channel_id}&type=video"
        f"&order=date&publishedAfter={published_after}&maxResults=5&key={api_key}"
    )
    with urllib.request.urlopen(_YOUTUBE_SEARCH_URL + params, timeout=15) as resp:
        data = json.loads(resp.read())

    results = []
    for item in data.get("items", []):
        vid_id = item.get("id", {}).get("videoId", "")
        pub = item.get("snippet", {}).get("publishedAt", utc_now_iso())
        if vid_id:
            results.append((f"https://www.youtube.com/watch?v={vid_id}", pub))
    return results


# ── Podcast RSS ───────────────────────────────────────────────────────────────

def _get_recent_podcast_episodes(rss_url: str, cutoff: datetime) -> List[Tuple[str, str]]:
    """Return [(episode_url, published_at_iso)] for episodes published after cutoff."""
    with urllib.request.urlopen(rss_url, timeout=15) as resp:
        root = ET.fromstring(resp.read())

    results = []
    for item in root.findall(".//item"):
        pub_raw = item.findtext("pubDate", "")
        try:
            pub_dt = parsedate_to_datetime(pub_raw).astimezone(timezone.utc)
        except Exception:
            continue
        if pub_dt < cutoff:
            continue

        # Prefer enclosure URL (audio file), fall back to link
        enclosure = item.find("enclosure")
        url = (
            enclosure.get("url", "") if enclosure is not None
            else item.findtext("link", "")
        )
        if url:
            results.append((url, pub_dt.isoformat()))
    return results


# ── Manual URL input ──────────────────────────────────────────────────────────

def _load_manual_urls(
    manual_dir: Path,
    ref: date,
    groq_api_key: str,
    provider,
    transcribe_fn,
    summarize_fn,
) -> List[RawItem]:
    """Process URLs from data/media/YYYY-WXX-urls.txt."""
    iso = ref.isocalendar()
    week_label = f"{iso[0]}-W{iso[1]:02d}"
    url_file = manual_dir / "media" / f"{week_label}-urls.txt"

    if not url_file.exists():
        return []

    items = []
    for line in url_file.read_text(encoding="utf-8").splitlines():
        url = line.strip()
        if not url or url.startswith("#"):
            continue
        item = _process_url(
            url, "手动输入", utc_now_iso(),
            groq_api_key, provider, transcribe_fn, summarize_fn,
        )
        if item:
            items.append(item)
    return items


# ── Core: download → transcribe → summarize ───────────────────────────────────

def _process_url(
    url: str,
    source_name: str,
    published_at: str,
    groq_api_key: str,
    provider,
    transcribe_fn,
    summarize_fn,
) -> Optional[RawItem]:
    print(f"[媒体] 处理 {source_name}: {url[:70]}", flush=True)

    # Fast path 1: Spotify episode transcript (seconds, no audio download)
    if "open.spotify.com/episode/" in url:
        transcript = _fetch_spotify_transcript(url)
        if transcript and len(transcript) >= _MIN_TRANSCRIPT_CHARS:
            print(f"[媒体] Spotify转录成功 ({len(transcript)} 字符)…", flush=True)
            return summarize_fn(transcript, url, source_name, published_at, provider)
        print("[媒体] Spotify转录不可用，尝试其他方式…", flush=True)
        return None  # Spotify links have no audio fallback

    # Fast path 1b: generic web transcript page (Substack, blog, etc.)
    if not ("youtube.com/watch" in url or "youtu.be/" in url):
        transcript = _fetch_web_transcript(url)
        if transcript and len(transcript) >= _MIN_TRANSCRIPT_CHARS:
            print(f"[媒体] 网页transcript获取成功 ({len(transcript)} 字符)…", flush=True)
            return summarize_fn(transcript, url, source_name, published_at, provider)
        print("[媒体] 网页transcript内容不足，跳过", flush=True)
        return None

    if not shutil.which("yt-dlp"):
        print("[媒体] ✗ yt-dlp 未安装，请运行: pip install yt-dlp", flush=True)
        return None

    # Fast path 2: YouTube auto-captions (seconds, no Groq needed)
    if "youtube.com/watch" in url or "youtu.be/" in url:
        transcript = _fetch_youtube_captions(url)
        if transcript and len(transcript) >= _MIN_TRANSCRIPT_CHARS:
            print(f"[媒体] YouTube字幕获取成功 ({len(transcript)} 字符)…", flush=True)
            return summarize_fn(transcript, url, source_name, published_at, provider)
        print("[媒体] 无自动字幕，回退到音频转录…", flush=True)

    # Slow path: download audio → Groq Whisper
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_path = _download_audio(url, Path(tmpdir))
        if not audio_path:
            return None

        print(f"[媒体] Groq转录中 ({audio_path.stat().st_size // 1024} KB)…", flush=True)
        transcript = transcribe_fn(audio_path, groq_api_key)
        if not transcript or len(transcript) < _MIN_TRANSCRIPT_CHARS:
            print("[媒体] 转录结果过短，跳过", flush=True)
            return None

        print(f"[媒体] 摘要生成中 ({len(transcript)} 字符转录)…", flush=True)
        return summarize_fn(transcript, url, source_name, published_at, provider)


# ── Spotify transcript (fast path) ───────────────────────────────────────────

def _fetch_spotify_transcript(episode_url: str) -> Optional[str]:
    """Fetch transcript from Spotify using anonymous web player token."""
    import json as _json
    episode_id = episode_url.split("/episode/")[-1].split("?")[0].strip()

    # Step 1: get anonymous access token (no login required)
    try:
        req = urllib.request.Request(
            "https://open.spotify.com/get_access_token?reason=transport&productType=web_player",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://open.spotify.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            token = _json.loads(resp.read()).get("accessToken", "")
    except Exception as exc:
        print(f"[媒体] Spotify token获取失败: {exc}", flush=True)
        return None

    if not token:
        return None

    # Step 2: fetch transcript via spclient API
    try:
        req = urllib.request.Request(
            f"https://spclient.wg.spotify.com/transcript-read-along/v2/episode/{episode_id}?format=json&market=from_token",
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "App-Platform": "WebPlayer",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = _json.loads(resp.read())
    except Exception as exc:
        print(f"[媒体] Spotify transcript API失败: {exc}", flush=True)
        return None

    # Parse transcript segments into plain text
    segments = data.get("section", [])
    if not segments:
        # Try flat "startMs/text" format
        segments = data.get("transcript", {}).get("section", [])

    lines = []
    for section in segments:
        for word_group in section.get("startMs", []):
            pass  # wrong structure
        # Flat word list under each section
        for item in section.get("body", {}).get("sentence", []):
            text = item.get("text", "")
            if text:
                lines.append(text)

    if not lines:
        # Try alternative key layout
        for item in data.get("body", {}).get("sentence", []):
            text = item.get("text", "")
            if text:
                lines.append(text)

    return " ".join(lines).strip() if lines else None


# ── YouTube auto-captions (fast path) ────────────────────────────────────────

def _fetch_youtube_captions(url: str) -> Optional[str]:
    """Download auto-generated captions via yt-dlp (no audio, seconds)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out = str(Path(tmpdir) / "cap")
        cmd = [
            "yt-dlp",
            "--write-auto-sub", "--sub-lang", "en",
            "--sub-format", "vtt",
            "--skip-download",
            "--no-playlist", "--quiet",
            "--output", out,
            url,
        ]
        try:
            subprocess.run(cmd, check=True, timeout=30, capture_output=True)
        except Exception:
            return None

        for f in Path(tmpdir).iterdir():
            if f.suffix == ".vtt":
                return _parse_vtt(f.read_text(encoding="utf-8", errors="ignore"))
    return None


def _parse_vtt(vtt: str) -> str:
    """Strip VTT timestamps and deduplicate lines into plain text."""
    import re as _re
    lines = []
    seen = set()
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or _re.match(r"^\d+$", line):
            continue
        # Strip inline tags like <c>, </c>, <00:00:00.000>
        clean = _re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in seen:
            seen.add(clean)
            lines.append(clean)
    return " ".join(lines)


def _fetch_web_transcript(url: str) -> Optional[str]:
    """Fetch and extract article/transcript text from a web page."""
    import re as _re
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        print(f"[媒体] 网页抓取失败: {exc}", flush=True)
        return None

    # Try article body (Substack: .body.markup, generic: <article>, <main>)
    for pattern in [
        r'<div[^>]*class="body markup"[^>]*>(.*)',
        r'<article[^>]*>(.*?)</article>',
        r'<main[^>]*>(.*?)</main>',
    ]:
        m = _re.search(pattern, html, _re.DOTALL)
        if m:
            raw = m.group(1)
            raw = _re.sub(r'<script[^>]*>.*?</script>', ' ', raw, flags=_re.DOTALL)
            raw = _re.sub(r'<style[^>]*>.*?</style>', ' ', raw, flags=_re.DOTALL)
            raw = _re.sub(r'<[^>]+>', ' ', raw)
            text = _re.sub(r'\s+', ' ', raw).strip()
            if len(text) >= _MIN_TRANSCRIPT_CHARS:
                return text[:50000]

    return None


def _download_audio(url: str, output_dir: Path) -> Optional[Path]:
    """Download audio-only stream via yt-dlp. Returns path to downloaded file."""
    out_template = str(output_dir / "audio.%(ext)s")
    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--max-filesize", "24M",
        "--no-playlist",
        "--quiet",
        "--output", out_template,
        url,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120, capture_output=True)
    except subprocess.CalledProcessError as exc:
        print(f"[媒体] yt-dlp 下载失败: {exc.stderr.decode()[:200]}", flush=True)
        return None
    except subprocess.TimeoutExpired:
        print("[媒体] yt-dlp 下载超时（120s）", flush=True)
        return None

    for f in output_dir.iterdir():
        if f.suffix in (".mp3", ".m4a", ".webm", ".ogg"):
            return f
    return None
