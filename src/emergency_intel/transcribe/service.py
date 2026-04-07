"""Audio transcription via Groq Whisper API (whisper-large-v3-turbo)."""
from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

_GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
_GROQ_MODEL = "whisper-large-v3-turbo"
_MAX_BYTES = 24 * 1024 * 1024  # 24 MB (Groq hard limit is 25 MB)
_BOUNDARY = "GEIBoundary20260405"


def transcribe_audio_file(audio_path: Path, groq_api_key: str, language: str = "en") -> str:
    """
    Transcribe a local audio file via Groq Whisper API.
    Returns the transcript text, or empty string on any failure.
    """
    if not groq_api_key:
        return ""

    size = audio_path.stat().st_size
    if size > _MAX_BYTES:
        print(
            f"[转录] 跳过 {audio_path.name}：文件 {size // 1024 // 1024} MB 超过 24 MB 上限",
            flush=True,
        )
        return ""

    audio_bytes = audio_path.read_bytes()
    body = _build_multipart(audio_path.name, audio_bytes)

    req = urllib.request.Request(
        _GROQ_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": f"multipart/form-data; boundary={_BOUNDARY}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read().decode("utf-8").strip()
    except urllib.error.HTTPError as exc:
        print(f"[转录] Groq API 错误 {exc.code}: {exc.read().decode()[:200]}", flush=True)
        return ""
    except Exception as exc:
        print(f"[转录] 转录失败: {exc}", flush=True)
        return ""


def _build_multipart(filename: str, audio_bytes: bytes) -> bytes:
    def field(name: str, value: str) -> bytes:
        return (
            f"--{_BOUNDARY}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()

    header = (
        f"--{_BOUNDARY}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: audio/mpeg\r\n\r\n"
    ).encode()

    return (
        field("model", _GROQ_MODEL)
        + field("response_format", "text")
        + field("language", "en")
        + header
        + audio_bytes
        + f"\r\n--{_BOUNDARY}--\r\n".encode()
    )
