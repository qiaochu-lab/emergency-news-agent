from __future__ import annotations

import re
from collections import Counter, defaultdict
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Dict, List

from emergency_intel.models import AnalyzedItem, WeeklyReport
from emergency_intel.utils import ensure_dir


DOMAINS = ["AI", "Communications", "Aviation", "DisasterTech"]
# DisasterTech 为可选专栏：有内容才输出，无内容不强求
OPTIONAL_DOMAINS = {"DisasterTech"}
REPORT_TITLE = "应急通信行业情报周报"
DOMAIN_NAMES_ZH = {
    "AI": "🤖 AI 专栏 — 前沿模型 / 智能体 / 多模态",
    "Communications": "📡 通信专栏 — 卫星通信 / 5G·6G / 专网",
    "Aviation": "✈️ 航空专栏 — 无人机 / 飞艇 / 低空系统",
    "DisasterTech": "💡 应急视角思考 — 本周可借鉴内容",
}
SOURCE_TYPE_ZH = {
    "official": "官方机构",
    "news": "行业媒体",
    "company": "企业博客",
    "blog": "专家博客",
    "paper": "学术论文",
    "forum": "社区论坛",
}
DOMAIN_EMPTY_SUMMARIES = {
    "AI": "本周 AI 方向高信号事件偏少，主题仍以模型能力向垂直场景渗透和应用落地验证为主。",
    "Communications": "本周通信方向新增高优先级信号有限，仍需持续观察 NTN、专网、5G-A、卫星直连和韧性通信链路演进。",
    "Aviation": "本周无人机与航空方向暂无强势新事件，建议继续跟踪空中中继、BVLOS 监管和飞艇平台进展。",
    "DisasterTech": None,  # None 表示该专栏无内容时整体跳过，不显示空文案
}

MAX_DOMAIN_ITEMS = 10
MAX_FEATURED_ITEMS = 5

# Known LLM output key prefixes that should not appear in rendered text
_KV_PREFIX_RE = re.compile(
    r"\b(?:technical_breakthrough|institutional_innovation|operational_innovation"
    r"|technical_focus|innovation|potential_impact|decision_relevance"
    r"|why_this_week|market_implications|industry_impact|operational_meaning"
    r"|downstream_impact|implications|conclusion|follow_up|signals_to_track"
    r"|next_step|watch_items|event_overview|short_term|medium_term|long_term"
    r")\s*[：:]\s*",
    re.IGNORECASE,
)


# ──────────────────────────────────────────────
# Text cleaning helpers
# ──────────────────────────────────────────────

def _clean_labeled_text(text: str) -> str:
    """Strip 'key: ' prefix patterns left over from LLM structured output."""
    if not text:
        return ""
    cleaned = _KV_PREFIX_RE.sub("", text)
    cleaned = re.sub(r"；+", "；", cleaned)
    cleaned = re.sub(r"[；;]\s*$", "", cleaned.strip())
    return " ".join(cleaned.split())


def _extract_kv_segment(text: str, key: str) -> str:
    """Extract the value for a named key from a 'key: value; key: value' string."""
    if not text:
        return ""
    pattern = (
        rf"(?:^|[；;])\s*{re.escape(key)}\s*[：:]\s*(.*?)(?=[；;]\s*\w+\s*[：:]|$)"
    )
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"[；;]+$", "", match.group(1).strip()).strip()
    return ""


def _clean_sentence(text: str) -> str:
    cleaned = " ".join((text or "").split())
    cleaned = cleaned.replace("标题:", "").replace("正文:", "")
    return cleaned.strip()


def _ensure_complete_sentence(text: str) -> str:
    """Trim text to last complete sentence to avoid mid-sentence cutoffs."""
    if not text:
        return ""
    text = text.strip()
    # If already ends with punctuation, return as-is
    if text and text[-1] in "。.！!？?」』":
        return text
    # Find the last sentence boundary
    for punct in ("。", "！", "？", ".", "!", "?"):
        idx = text.rfind(punct)
        if idx > len(text) // 2:
            return text[: idx + 1]
    return text


def _fallback_summary(item: AnalyzedItem) -> str:
    return (item.raw_text[:220] + "...") if len(item.raw_text) > 220 else item.raw_text


def _format_domains(domains: List[str]) -> str:
    return "、".join(DOMAIN_NAMES_ZH.get(d, d) for d in domains)


def _format_week_range(week_range: str) -> str:
    parts = week_range.split(" to ")
    if len(parts) != 2:
        return week_range
    return f"{parts[0].replace('-', '.')} — {parts[1].replace('-', '.')}"


def _short_date(published_at: str) -> str:
    if not published_at:
        return "时间待补"
    cleaned = published_at.strip()
    try:
        return parsedate_to_datetime(cleaned).strftime("%Y.%m.%d")
    except Exception:
        return cleaned[:10].replace("-", ".")


# ──────────────────────────────────────────────
# Field extraction helpers
# ──────────────────────────────────────────────

def _get_clean_summary(item: AnalyzedItem) -> str:
    text = item.summary or item.raw_text[:300]
    return _clean_labeled_text(text) or _fallback_summary(item)


def _get_clean_innovation(item: AnalyzedItem) -> str:
    if not item.innovation:
        return ""
    return _clean_labeled_text(item.innovation)


def _get_decision_relevance(item: AnalyzedItem) -> str:
    if not item.takeaway:
        return ""
    extracted = _extract_kv_segment(item.takeaway, "decision_relevance")
    if extracted:
        return _ensure_complete_sentence(_clean_labeled_text(extracted))
    cleaned = _clean_labeled_text(item.takeaway)
    parts = [p.strip() for p in re.split(r"[；;]", cleaned) if len(p.strip()) > 20]
    return _ensure_complete_sentence(parts[0]) if parts else _ensure_complete_sentence(cleaned[:300])


def _get_follow_up_items(item: AnalyzedItem) -> List[str]:
    if not item.takeaway:
        return _default_follow_up(item)
    extracted = _extract_kv_segment(item.takeaway, "follow_up")
    if extracted:
        cleaned = _clean_labeled_text(extracted)
        tips = [t.strip() for t in re.split(r"[；;。\n]", cleaned) if len(t.strip()) > 8]
        if tips:
            return tips[:3]
    return _default_follow_up(item)


def _default_follow_up(item: AnalyzedItem) -> List[str]:
    if item.source_type == "official":
        return ["持续关注相关政策文件和预算安排", "跟踪后续采购或标准化进展", "观察国际同类动向"]
    if item.source_type == "paper":
        return ["关注代码开源或复现进展", "跟踪工业界是否跟进落地", "观察同类研究后续发表"]
    return ["关注后续报道和合作扩散", "跟踪商业落地信号", "观察权威来源是否印证"]


def _simple_judgment(item: AnalyzedItem) -> str:
    """One-line clean judgment suitable for tables."""
    if item.takeaway:
        extracted = _extract_kv_segment(item.takeaway, "decision_relevance")
        if extracted:
            text = _clean_labeled_text(extracted)
            text = _ensure_complete_sentence(text[:120])
            return text
    if item.summary:
        text = _clean_labeled_text(item.summary)
        text = _ensure_complete_sentence(text[:120])
        return text
    return f"{_format_domains(item.domain_tags)}方向值得继续跟踪。"


# ──────────────────────────────────────────────
# Report builder
# ──────────────────────────────────────────────

def build_weekly_report(items: List[AnalyzedItem], week_range: str) -> WeeklyReport:
    primary_items = [item for item in items if item.include_in_top_report]
    supplementary = [
        item for item in items
        if item.is_this_week_signal
        and item.report_content_type not in {"resource", "podcast", "landing_page"}
        and item.final_score >= 2.5
    ]

    seen_ids: set = set()
    selected_items: List[AnalyzedItem] = []
    for item in primary_items + supplementary:
        if item.id not in seen_ids:
            seen_ids.add(item.id)
            selected_items.append(item)
    selected_items = selected_items[:40]

    grouped: Dict[str, List[AnalyzedItem]] = defaultdict(list)
    for item in selected_items:
        for tag in item.domain_tags:
            if tag in DOMAINS:
                grouped[tag].append(item)

    section_summaries: Dict[str, str] = {}
    for domain in DOMAINS:
        domain_items = grouped.get(domain, [])
        if domain_items:
            section_summaries[domain] = _section_summary(domain_items)
        elif domain not in OPTIONAL_DOMAINS:
            section_summaries[domain] = DOMAIN_EMPTY_SUMMARIES[domain]
        # OPTIONAL_DOMAINS (e.g. DisasterTech) are omitted entirely when empty

    weekly_insights = _cross_domain_insights(selected_items)
    return WeeklyReport(
        week_range=week_range,
        selected_items=selected_items,
        section_summaries=section_summaries,
        weekly_insights=weekly_insights,
    )


# Domain caps for the deep-dive section (max items per domain)
_DOMAIN_CAPS = {
    "AI": 3,
    "Communications": 3,
    "Aviation": 2,
    "DisasterTech": 2,
}


def _select_balanced_featured(items: List[AnalyzedItem], max_count: int) -> List[AnalyzedItem]:
    """Pick up to max_count items ensuring cross-domain coverage.

    Strategy:
    1. Take the highest-scoring item from each domain (round-robin by score).
    2. Fill remaining slots with globally highest-scoring items not yet chosen.
    3. Never pick the same item twice. Never exceed domain caps.
    """
    by_domain: Dict[str, List[AnalyzedItem]] = defaultdict(list)
    for item in items:
        for tag in item.domain_tags:
            if tag in DOMAINS:
                by_domain[tag].append(item)
    # Sort each domain bucket by score desc
    for domain in by_domain:
        by_domain[domain].sort(key=lambda x: x.final_score, reverse=True)

    selected: List[AnalyzedItem] = []
    seen_ids: set = set()
    domain_counts: Dict[str, int] = defaultdict(int)

    # Round 1: one top item per domain (priority order: Comms > AI > Aviation > DisasterTech)
    priority_order = ["Communications", "AI", "Aviation", "DisasterTech"]
    for domain in priority_order:
        if len(selected) >= max_count:
            break
        for candidate in by_domain.get(domain, []):
            cap = _DOMAIN_CAPS.get(domain, 2)
            if candidate.id not in seen_ids and domain_counts[domain] < cap:
                selected.append(candidate)
                seen_ids.add(candidate.id)
                domain_counts[domain] += 1
                break

    # Round 2: fill remaining slots from global pool, respecting caps
    global_sorted = sorted(items, key=lambda x: x.final_score, reverse=True)
    for candidate in global_sorted:
        if len(selected) >= max_count:
            break
        if candidate.id in seen_ids:
            continue
        # Check if any of its domains still has capacity
        candidate_domains = [t for t in candidate.domain_tags if t in DOMAINS]
        if not candidate_domains:
            continue
        primary_domain = candidate_domains[0]
        cap = _DOMAIN_CAPS.get(primary_domain, 2)
        if domain_counts[primary_domain] < cap:
            selected.append(candidate)
            seen_ids.add(candidate.id)
            domain_counts[primary_domain] += 1

    return selected


# ──────────────────────────────────────────────
# Main render entry point
# ──────────────────────────────────────────────

def render_report_markdown(report: WeeklyReport, output_path: Path) -> str:
    ensure_dir(output_path.parent)
    rating = _report_rating(report)

    domain_groups: Dict[str, List[AnalyzedItem]] = defaultdict(list)
    for item in report.selected_items:
        for tag in item.domain_tags:
            if tag in DOMAINS:
                domain_groups[tag].append(item)

    featured = _select_balanced_featured(report.selected_items, MAX_FEATURED_ITEMS)

    lines: List[str] = []

    # ── Cover / Header ──
    lines += [
        f"# {REPORT_TITLE}",
        "",
        f"**{_format_week_range(report.week_range)}**",
        "",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 研报评级 | {rating} |",
        "| 覆盖领域 | AI · 无人机 · 通信网络 · 泛应急 |",
        f"| 本期信号数 | {len(report.selected_items)} 条 |",
        f"| 生成时间 | {report.generated_at[:16].replace('T', ' ')} |",
        "",
        "---",
        "",
    ]

    # ── Executive Summary ──
    lines += ["## 执行摘要", ""]
    lines += _render_exec_summary_table(report, rating)
    lines += ["", _market_summary(report), "", "---", ""]

    # ── Table of Contents ──
    lines += [
        "## 目录",
        "",
        "1. [本周概览](#一本周概览)",
        "2. [重点事件深度分析](#二重点事件深度分析)",
        "3. [各领域精选动态](#三各领域精选动态)",
        "4. [事件日历](#四事件日历)",
        "5. [建议与风险](#五建议与风险)",
        "- [附录：本期信源列表](#附录本期信源列表)",
        "",
        "---",
        "",
    ]

    # ── Chapter 1 ──
    lines += ["## 一、本周概览", ""]
    lines += _render_overview_chapter(report, domain_groups)
    lines += ["---", ""]

    # ── Chapter 2 ──
    lines += ["## 二、重点事件深度分析", ""]
    if featured:
        for idx, item in enumerate(featured, 1):
            lines += _render_featured_item(idx, item)
    else:
        lines += [
            "本周进入主体报告的高信号事件数量有限，当前更适合继续扩充高质量信源并观察后续催化。",
            "",
            "---",
            "",
        ]

    # ── Chapter 3 ──
    lines += ["## 三、各领域精选动态", ""]
    chapter3_seen: set = set()
    sec_idx = 1
    for domain in DOMAINS:
        domain_items = domain_groups.get(domain, [])
        # Skip optional domains with no content
        if domain in OPTIONAL_DOMAINS and not domain_items:
            continue
        lines += _render_domain_section(sec_idx, domain, domain_items, chapter3_seen)
        sec_idx += 1
    lines += ["---", ""]

    # ── Chapter 4 ──
    lines += ["## 四、事件日历", ""]
    lines += _render_calendar_chapter(report)
    lines += ["---", ""]

    # ── Chapter 5 ──
    lines += ["## 五、建议与风险", ""]
    lines += _render_recommendations_chapter(report)
    lines += ["---", ""]

    # ── Appendix ──
    lines += ["## 附录：本期信源列表", ""]
    lines += _render_source_appendix(report)

    markdown = "\n".join(lines).strip() + "\n"
    with output_path.open("w", encoding="utf-8") as fh:
        fh.write(markdown)
    return markdown


# ──────────────────────────────────────────────
# Chapter renderers
# ──────────────────────────────────────────────

def _render_exec_summary_table(report: WeeklyReport, rating: str) -> List[str]:
    top = report.selected_items[0] if report.selected_items else None
    top_title = (top.title[:30] + "...") if top and len(top.title) > 30 else (top.title if top else "—")
    insight = report.weekly_insights[0] if report.weekly_insights else "本周主线以高确定性事件驱动为主"
    risk = _risk_lines(report)[0] if report.selected_items else "信源样本不足，建议扩充采集范围"
    return [
        "| 维度 | 本周判断 |",
        "|------|---------|",
        f"| 景气度 | {_market_summary_short(report)} |",
        f"| 核心主线 | {insight} |",
        f"| 重点事件 | {top_title} |",
        f"| 风险提示 | {risk} |",
    ]


def _render_overview_chapter(
    report: WeeklyReport,
    domain_groups: Dict[str, List[AnalyzedItem]],
) -> List[str]:
    lines: List[str] = [
        "### 1.1 行业整体表现",
        "",
        _market_summary(report),
        "",
    ]
    for line in _market_supporting_lines(report):
        lines.append(f"- {line}")
    lines.append("")

    lines += [
        "### 1.2 各领域信号分布",
        "",
        "| 领域 | 本周信号数 | 强弱判断 | 代表性事件 |",
        "|------|-----------|---------|-----------|",
    ]
    for domain in DOMAINS:
        items = domain_groups.get(domain, [])
        count = len(items)
        strength = "强" if count >= 3 else ("中" if count >= 1 else "弱")
        rep_title = items[0].title if items else ""
        rep = (rep_title[:25] + "...") if len(rep_title) > 25 else (rep_title or "—")
        lines.append(f"| {DOMAIN_NAMES_ZH[domain]} | {count} | {strength} | {rep} |")
    lines.append("")

    lines += ["### 1.3 重点主体动态", ""]
    if report.selected_items:
        for item in report.selected_items[:5]:
            judgment = _simple_judgment(item)
            lines.append(f"- **{item.title}**（{item.source_name}）：{judgment}")
    else:
        lines.append("- 当前暂无足够强的代表性主体进入重点观察名单。")
    lines.append("")

    return lines


def _render_featured_item(index: int, item: AnalyzedItem) -> List[str]:
    date_str = _short_date(item.published_at)
    domain_str = _format_domains(item.domain_tags)
    title_link = f"[{item.title}]({item.url})" if item.url else item.title

    lines = [
        f"### 2.{index} {item.title}",
        "",
        f"> **来源：** {item.source_name}　｜　**日期：** {date_str}　｜　**领域：** {domain_str}",
        "",
    ]

    summary_text = _get_clean_summary(item)
    if summary_text:
        lines += ["**事件概述**", "", summary_text, ""]

    if item.key_points:
        lines += ["**核心要点**", ""]
        for kp in item.key_points[:4]:
            clean_kp = _clean_labeled_text(str(kp)) if kp else ""
            if clean_kp:
                lines.append(f"- {clean_kp}")
        lines.append("")

    innovation_text = _get_clean_innovation(item)
    if innovation_text:
        lines += ["**分析判断**", "", innovation_text, ""]

    decision_text = _get_decision_relevance(item)
    if decision_text:
        lines += ["**决策启示**", "", decision_text, ""]

    follow_up_items = _get_follow_up_items(item)
    if follow_up_items:
        lines += ["**跟踪建议**", ""]
        for tip in follow_up_items:
            lines.append(f"- {tip}")
        lines.append("")

    if item.url:
        lines += [f"**原文链接：** {title_link}", ""]

    lines += ["---", ""]
    return lines


def _render_domain_section(
    section_idx: int,
    domain: str,
    items: List[AnalyzedItem],
    seen_ids: set | None = None,
) -> List[str]:
    domain_name = DOMAIN_NAMES_ZH[domain]
    lines = [f"### 3.{section_idx} {domain_name}", ""]

    if seen_ids is None:
        seen_ids = set()

    # Deduplicate: only show items not already shown in a previous domain section
    unique_items = [it for it in items if it.id not in seen_ids]
    if not unique_items:
        empty_msg = DOMAIN_EMPTY_SUMMARIES.get(domain)
        if empty_msg:
            lines += [empty_msg, "", ""]
        return lines

    domain_items = unique_items[:MAX_DOMAIN_ITEMS]
    for it in domain_items:
        seen_ids.add(it.id)

    lines.append(f"精选本周高信号事件（共 {len(domain_items)} 条）：")
    lines.append("")

    for i, item in enumerate(domain_items, 1):
        summary = _get_clean_summary(item)
        short_summary = (summary[:150] + "...") if len(summary) > 150 else summary
        date_str = _short_date(item.published_at)
        title_part = f"[{item.title}]({item.url})" if item.url else item.title
        lines.append(f"{i}. **{title_part}**")
        if short_summary:
            lines.append(f"   {short_summary}")
        lines.append(f"   `{item.source_name} | {date_str}`")
        lines.append("")

    return lines


def _render_calendar_chapter(report: WeeklyReport) -> List[str]:
    lines = ["### 本周重要事件", ""]
    if report.selected_items:
        lines += [
            "| 日期 | 事件标题 | 来源 | 要点 |",
            "|------|---------|------|------|",
        ]
        for item in report.selected_items[:6]:
            date_str = _short_date(item.published_at)
            short_title = (item.title[:28] + "...") if len(item.title) > 28 else item.title
            judgment = _simple_judgment(item)
            short_judgment = (judgment[:38] + "...") if len(judgment) > 38 else judgment
            lines.append(f"| {date_str} | {short_title} | {item.source_name} | {short_judgment} |")
    else:
        lines.append("本周已发生的重要事件相对有限，建议继续围绕政策、项目和产业会议做补充跟踪。")

    lines += ["", "### 下周跟踪重点", ""]
    for line in _next_week_event_lines(report):
        lines.append(line)
    lines.append("")
    return lines


def _render_recommendations_chapter(report: WeeklyReport) -> List[str]:
    lines = ["### 建议关注方向", ""]
    for line in _focus_directions(report):
        lines.append(f"- {line}")
    lines += ["", "### 风险提示", ""]
    for line in _risk_lines(report):
        lines.append(f"- {line}")
    lines.append("")
    return lines


def _render_source_appendix(report: WeeklyReport) -> List[str]:
    if not report.selected_items:
        return ["本期暂无来源记录。", ""]

    seen_sources: Dict[str, AnalyzedItem] = {}
    for item in report.selected_items:
        if item.source_name not in seen_sources:
            seen_sources[item.source_name] = item

    source_item_count = Counter(item.source_name for item in report.selected_items)

    lines = [
        "| # | 来源名称 | 类型 | 领域 | 本期条目数 | 代表链接 |",
        "|---|---------|------|------|-----------|---------|",
    ]
    for idx, (source_name, rep_item) in enumerate(seen_sources.items(), 1):
        source_type_zh = SOURCE_TYPE_ZH.get(rep_item.source_type, rep_item.source_type)
        domain_tags = sorted({
            tag for item in report.selected_items
            if item.source_name == source_name
            for tag in item.domain_tags
        })
        domain_zh = "、".join(DOMAIN_NAMES_ZH.get(d, d)[:4] for d in domain_tags[:2])
        count = source_item_count[source_name]
        link = f"[链接]({rep_item.url})" if rep_item.url else "—"
        lines.append(f"| {idx} | {source_name} | {source_type_zh} | {domain_zh} | {count} | {link} |")

    lines.append("")
    return lines


# ──────────────────────────────────────────────
# Insight / summary helpers
# ──────────────────────────────────────────────

def _section_summary(items: List[AnalyzedItem]) -> str:
    top = items[0]
    return (
        f"本周该方向共识别 {len(items)} 条重点信号，"
        f"其中「{top.title}」代表性最强，说明相关能力和场景推进仍在持续。"
    )


def _cross_domain_insights(items: List[AnalyzedItem]) -> List[str]:
    if not items:
        return ["本周样本不足，建议继续扩充高质量公开信息源。"]
    insights: List[str] = []
    if any(len(item.domain_tags) > 1 for item in items):
        insights.append("跨领域信号仍在增加，AI、通信、无人系统与应急体系开始出现更明显的耦合。")
    if any(item.source_type == "official" for item in items):
        insights.append("官方来源仍是高价值线索的主要来源，政策、标准和部署动向值得优先跟踪。")
    if any(item.source_type == "paper" for item in items):
        insights.append("论文和产业信号之间开始形成联动，前沿研究向场景落地的路径值得继续观察。")
    if not insights:
        insights.append("本周高信号主要来自单点事件，后续仍需等待更强的产业共振。")
    return insights


def _report_rating(report: WeeklyReport) -> str:
    if not report.selected_items:
        return "中性"
    avg_score = sum(item.final_score for item in report.selected_items) / max(1, len(report.selected_items))
    if avg_score >= 8:
        return "推荐"
    if avg_score >= 6:
        return "中性偏积极"
    return "中性"


def _market_summary(report: WeeklyReport) -> str:
    if not report.selected_items:
        return "本周泛应急技术相关主题整体表现偏平，尚未形成足够强的主线共振。"
    if any(len(item.domain_tags) > 1 for item in report.selected_items):
        return "本周泛应急技术相关主题整体维持活跃，跨领域融合方向仍是景气度相对较高的主线。"
    return "本周泛应急技术相关主题以结构性演进为主，主线更多体现在局部场景和细分方向。"


def _market_summary_short(report: WeeklyReport) -> str:
    if not report.selected_items:
        return "整体偏平，待形成共振"
    if any(len(item.domain_tags) > 1 for item in report.selected_items):
        return "整体活跃，跨领域融合驱动"
    return "结构性演进，局部场景主导"


def _market_supporting_lines(report: WeeklyReport) -> List[str]:
    if not report.selected_items:
        return [
            "主要驱动因素仍不足以形成板块级共振，后续需要更多政策、项目或产业化信号确认。",
            "从运行结果看，当前更应优先补齐高质量官方源、论文源和产业会议源。",
        ]
    lines = [
        f"本周共筛出 {len(report.selected_items)} 条重点事件，覆盖 {_watch_directions(report)} 等方向。",
        f"高价值来源主要来自 {_top_source_names(report, limit=3)}。",
    ]
    if any(item.source_type == "official" for item in report.selected_items):
        lines.append("官方公告和机构动向仍是最值得优先跟踪的线索来源。")
    if any(item.source_type == "paper" for item in report.selected_items):
        lines.append("学术论文信号本周有一定贡献，前沿研究向场景落地路径值得观察。")
    return lines[:4]


def _next_week_event_lines(report: WeeklyReport) -> List[str]:
    if not report.selected_items:
        return [
            "- 下周建议重点关注行业会议、政策发布和重点公司公告。",
            "- 如暂无明确事件日历，可优先跟踪高频主题是否出现进一步验证信号。",
        ]
    primary = report.selected_items[0]
    secondary = report.selected_items[1] if len(report.selected_items) > 1 else None
    title_short = primary.title[:30]
    lines = [
        f"- 优先跟踪「{title_short}」是否出现后续公告、合作落地或引用扩散。",
        f"- 持续观察 {_watch_directions(report)} 方向是否出现新的政策、会议或产品节点。",
    ]
    if secondary:
        sec_short = secondary.title[:30]
        lines.append(
            f"- 同时关注「{sec_short}」是否形成第二波催化，"
            "判断板块能否从主题演绎走向产业兑现。"
        )
    return lines


def _focus_directions(report: WeeklyReport) -> List[str]:
    if not report.selected_items:
        return [
            "技术主线：优先关注 AI、卫星互联网、韧性通信和无人系统的交叉方向。",
            "场景主线：持续跟踪灾害感知、指挥协同和临时通信保障场景。",
            "验证点：关注政策节奏、项目落地和真实部署案例。",
        ]
    domain_labels = _watch_directions(report)
    top_title = report.selected_items[0].title[:30]
    return [
        f"技术主线：建议持续关注 {domain_labels} 相关链条，重点看能力组合是否继续增强。",
        f"场景主线：围绕「{top_title}」所代表的应用场景，跟踪是否出现规模化部署或跨部门协同验证。",
        "验证点：优先观察政策升级、重点项目、预算投入、产业合作和应用落地信号。",
    ]


def _risk_lines(report: WeeklyReport) -> List[str]:
    risks = [
        "政策推进节奏不及预期风险",
        "产业落地节奏不及预期风险",
        "市场需求或项目预算不及预期风险",
    ]
    if any(item.source_type == "paper" for item in report.selected_items):
        risks.append("技术成熟度与工程化转化不及预期风险")
    else:
        risks.append("外部环境与供应链不确定性风险")
    return risks[:4]


def _watch_directions(report: WeeklyReport) -> str:
    watched = [
        DOMAIN_NAMES_ZH[domain]
        for domain in DOMAINS
        if any(domain in item.domain_tags for item in report.selected_items)
    ]
    return "、".join(watched[:4]) if watched else "AI、通信网络、无人系统与泛应急方向"


def _top_source_names(report: WeeklyReport, limit: int = 3) -> str:
    counter = Counter(item.source_name for item in report.selected_items)
    names = [name for name, _ in counter.most_common(limit)]
    return "、".join(names) if names else "暂无明显集中来源"
