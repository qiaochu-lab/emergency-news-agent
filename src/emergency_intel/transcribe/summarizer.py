"""Convert a raw transcript into a RawItem via LLM summarization."""
from __future__ import annotations

from typing import Optional

from emergency_intel.analyze.provider import ProviderClient, ProviderError, generate_structured_analysis
from emergency_intel.models import RawItem
from emergency_intel.utils import slugify, utc_now_iso

_PROMPT = """
你是应急通信行业周报的内容处理助手。以下是一段视频或播客的转录文字。
以 JSON 格式返回摘要，包含：
- title: string，简洁内容标题（30字以内，中文）
- summary: string，3-5句核心内容摘要（中文，结论前置）
- key_points: list of strings，3-5条关键要点（中文，每条不超过40字）
- domain_hint: string，内容所属领域（AI / Communications / Aviation / DisasterTech 之一）

规则：
- 只基于转录内容，不添加外部信息
- 专业术语首次出现时用括号补充中文解释
- 如内容与应急通信行业关联度低，在 summary 中如实说明
"""

_MAX_CHARS = 8000  # Groq whisper-large-v3-turbo outputs ~150 wpm; 60min ≈ 9000 words


def summarize_transcript(
    transcript: str,
    source_url: str,
    source_name: str,
    published_at: str,
    provider: ProviderClient,
) -> Optional[RawItem]:
    """
    Summarize transcript with LLM and return a RawItem.
    Returns None if transcript is too short or summarization fails.
    """
    if len(transcript.strip()) < 200:
        return None

    # Truncate: keep first 6000 + last 2000 chars to capture intro & conclusion
    if len(transcript) > _MAX_CHARS:
        text = transcript[:6000] + "\n…[中间部分省略]…\n" + transcript[-2000:]
    else:
        text = transcript

    try:
        result = generate_structured_analysis(text, _PROMPT, provider)
    except ProviderError:
        return None

    if not result or not result.get("summary"):
        return None

    summary = str(result.get("summary", ""))
    points = [str(p) for p in result.get("key_points", []) if p]
    raw_text = summary + " " + " ".join(points)

    return RawItem(
        id=f"media-{slugify(source_url[:80])}",
        source_type="blog",
        source_name=source_name,
        title=str(result.get("title", source_name[:60])),
        url=source_url,
        published_at=published_at or utc_now_iso(),
        language="zh",
        raw_text=raw_text,
        content_depth="fulltext",
        body_extraction_status="transcript_summarized",
    )
