from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, List

from emergency_intel.analyze.prompts import (
    ANALYSIS_PROMPT,
    FORUM_ANALYSIS_PROMPT,
    NEWS_ANALYSIS_PROMPT,
    OFFICIAL_ANALYSIS_PROMPT,
    PAPER_ANALYSIS_PROMPT,
    SCREENING_PROMPT,
)
from emergency_intel.analyze.provider import ProviderClient, ProviderError, generate_structured_analysis
from emergency_intel.models import AnalyzedItem, ScoredItem
from emergency_intel.utils import normalize_whitespace, write_json


_LLM_WORKERS = 5


def screen_items(
    items: Iterable[ScoredItem],
    output_path: Path,
    provider_client: ProviderClient,
    reference_date: date | None = None,
) -> List[ScoredItem]:
    item_list = list(items)
    heuristic_results = [_heuristic_screen(item, reference_date) for item in item_list]

    # Identify items that need LLM screening
    llm_candidates = [
        (i, item)
        for i, (item, result) in enumerate(zip(item_list, heuristic_results))
        if (
            provider_client.provider != "mock"
            and item.final_score >= 6.5
            and result.get("is_this_week_signal") is True
            and result.get("report_content_type") not in {"resource", "podcast", "landing_page"}
        )
    ]

    def _screen_one(idx_item):
        idx, item = idx_item
        prompt_input = _build_screening_prompt_input(item, reference_date)
        try:
            llm_result = generate_structured_analysis(prompt_input, SCREENING_PROMPT, provider_client)
            return idx, _merge_screening_result(heuristic_results[idx], llm_result)
        except ProviderError:
            return idx, heuristic_results[idx]

    if llm_candidates:
        with ThreadPoolExecutor(max_workers=_LLM_WORKERS) as executor:
            futures = {executor.submit(_screen_one, pair): pair[0] for pair in llm_candidates}
            for future in as_completed(futures):
                idx, merged = future.result()
                heuristic_results[idx] = merged

    screened: List[ScoredItem] = []
    for item, result in zip(item_list, heuristic_results):
        payload = dict(item.__dict__)
        payload.update(result)
        screened.append(ScoredItem(**payload))

    write_json(output_path, [entry.__dict__ for entry in screened])
    return screened


def analyze_items(
    items: Iterable[ScoredItem],
    output_path: Path,
    provider_client: ProviderClient,
    minimum_score: float,
) -> List[AnalyzedItem]:
    item_list = list(items)

    def _should_analyze(item: ScoredItem) -> bool:
        return (
            item.include_in_top_report
            or item.final_score >= minimum_score
            or (
                item.is_this_week_signal
                and item.report_content_type not in {"resource", "podcast", "landing_page"}
                and item.final_score >= 3.0
            )
        )

    def _analyze_one(item: ScoredItem) -> AnalyzedItem:
        if not _should_analyze(item):
            return AnalyzedItem(**item.__dict__)
        prompt_input = _build_prompt_input(item)
        prompt_template = _prompt_for_item(item)
        try:
            analysis = generate_structured_analysis(prompt_input, prompt_template, provider_client)
        except ProviderError:
            analysis = {}
        return AnalyzedItem(
            **item.__dict__,
            summary=str(analysis.get("summary", "")),
            key_points=[str(point) for point in analysis.get("key_points", [])],
            innovation=str(analysis.get("innovation", "")),
            takeaway=str(analysis.get("takeaway", "")),
            non_expert_explanation=str(analysis.get("non_expert_explanation", "")),
        )

    analyzed: List[AnalyzedItem] = [None] * len(item_list)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=_LLM_WORKERS) as executor:
        futures = {executor.submit(_analyze_one, item): i for i, item in enumerate(item_list)}
        for future in as_completed(futures):
            idx = futures[future]
            analyzed[idx] = future.result()

    write_json(output_path, [entry.__dict__ for entry in analyzed])
    return analyzed


def _build_prompt_input(item: ScoredItem) -> str:
    return (
        f"标题: {item.title}\n"
        f"来源: {item.source_name} ({item.source_type})\n"
        f"发布时间: {item.published_at}\n"
        f"领域: {', '.join(item.domain_tags)}\n"
        f"本周相关性: {item.why_this_week}\n"
        f"入选原因: {item.inclusion_reason}\n"
        f"分析备注: {item.analyst_note}\n"
        f"正文: {item.raw_text[:2200]}"
    )


def _build_screening_prompt_input(item: ScoredItem, reference_date: date | None) -> str:
    return (
        f"标题: {item.title}\n"
        f"来源: {item.source_name} ({item.source_type})\n"
        f"发布时间: {item.published_at}\n"
        f"参考周: {(reference_date or date.today()).isoformat()}\n"
        f"领域: {', '.join(item.domain_tags)}\n"
        f"链接: {item.url}\n"
        f"正文: {item.raw_text[:3000]}"
    )


def _merge_screening_result(base: dict[str, object], llm_result: dict[str, object]) -> dict[str, object]:
    merged = dict(base)
    for key in (
        "content_type",
        "why_this_week",
        "inclusion_reason",
        "analyst_note",
        "week_relevance",
    ):
        value = str(llm_result.get(key, "")).strip()
        if value:
            if key == "content_type":
                merged["report_content_type"] = value
            else:
                merged[key] = value
    for key in ("is_this_week_signal", "include_in_top_report"):
        value = llm_result.get(key)
        if isinstance(value, bool):
            merged[key] = value
        elif isinstance(value, str) and value.lower() in {"yes", "true", "no", "false"}:
            merged[key] = value.lower() in {"yes", "true"}
    for key in ("emergency_relevance_score", "communication_relevance_score"):
        value = llm_result.get(key)
        if isinstance(value, int):
            merged[key] = max(1, min(5, value))
        elif isinstance(value, str) and value.isdigit():
            merged[key] = max(1, min(5, int(value)))
    return merged


def _heuristic_screen(item: ScoredItem, reference_date: date | None) -> dict[str, object]:
    report_content_type = _infer_report_content_type(item)
    week_signal = _is_this_week_signal(item, reference_date)
    emergency_score = _relevance_score(item, target="emergency")
    communication_score = _relevance_score(item, target="communications")
    excluded_type = report_content_type in {"landing_page", "resource", "podcast"}
    strategic_signal = _is_strategic_signal(item)
    include = (
        not excluded_type
        and week_signal
        and (
            (item.final_score >= 4.5 and max(emergency_score, communication_score) >= 2)
            or (
                item.source_type in {"official", "company"}
                and item.final_score >= 3.0
                and strategic_signal
            )
            or (
                "AI" in item.domain_tags
                and item.final_score >= 3.0
                and strategic_signal
            )
        )
    )
    if (
        not include
        and item.source_type == "official"
        and week_signal
        and item.content_depth in {"fulltext", "fulltext_candidate"}
        and item.final_score >= 3.0
        and max(emergency_score, communication_score) >= 3
    ):
        include = True
    why_this_week = _why_this_week(item, week_signal)
    inclusion_reason = _inclusion_reason(item, include, report_content_type, week_signal)
    analyst_note = _analyst_note(item, report_content_type, include, week_signal)
    week_relevance = "high" if week_signal else "low"
    return {
        "report_content_type": report_content_type,
        "is_this_week_signal": week_signal,
        "why_this_week": why_this_week,
        "emergency_relevance_score": emergency_score,
        "communication_relevance_score": communication_score,
        "include_in_top_report": include,
        "inclusion_reason": inclusion_reason,
        "analyst_note": analyst_note,
        "week_relevance": week_relevance,
    }


def _infer_report_content_type(item: ScoredItem) -> str:
    text = normalize_whitespace(f"{item.title} {item.raw_text} {item.url}").lower()
    if item.source_type == "paper":
        return "paper"
    if any(term in text for term in ("podcast", "/podcast/", "episode", "debrief")):
        return "podcast"
    if any(term in text for term in ("small business", "communities", "work-with-us", "about us", "overview", "landing page")):
        return "resource"
    if any(term in text for term in ("directory", "community", "categories", "tag:", "archive")):
        return "resource"
    if item.source_type == "official":
        return "official_announcement"
    if item.source_type == "company":
        return "company_update"
    if item.source_type == "news":
        return "news"
    return "general"


def _is_this_week_signal(item: ScoredItem, reference_date: date | None) -> bool:
    published = _parse_date(item.published_at)
    if not published:
        return False
    ref = reference_date or date.today()
    start = ref.fromordinal(ref.toordinal() - ref.weekday() - 7)
    end = start.fromordinal(start.toordinal() + 6)
    return start <= published <= end


def _parse_date(value: str) -> date | None:
    cleaned = (value or "").strip().replace("Z", "+00:00")
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        try:
            return datetime.strptime(cleaned[:10], "%Y-%m-%d").date()
        except ValueError:
            try:
                return parsedate_to_datetime(value.strip()).date()
            except Exception:
                return None


def _relevance_score(item: ScoredItem, target: str) -> int:
    text = normalize_whitespace(f"{item.title} {item.raw_text} {' '.join(item.domain_tags)}").lower()
    if target == "emergency":
        keywords = ("emergency", "disaster", "rescue", "public safety", "response", "flood", "wildfire")
        domain_hit = "emergency response" in (tag.lower() for tag in item.domain_tags)
    else:
        keywords = ("communication", "network", "wireless", "satellite", "6g", "5g", "mesh", "ntn")
        domain_hit = "communications" in (tag.lower() for tag in item.domain_tags)
    score = 1
    if domain_hit:
        score += 2
    if any(keyword in text for keyword in keywords):
        score += 2
    return min(score, 5)


def _is_strategic_signal(item: ScoredItem) -> bool:
    text = normalize_whitespace(f"{item.title} {item.raw_text} {' '.join(item.domain_tags)}").lower()
    keywords = (
        "ai",
        "model",
        "agent",
        "autonomous",
        "autonomy",
        "drone",
        "uav",
        "helicopter",
        "robotics",
        "satellite",
        "wireless",
        "network",
        "communications",
        "safety",
        "security",
        "emergency",
        "resilience",
    )
    return any(keyword in text for keyword in keywords)


def _why_this_week(item: ScoredItem, week_signal: bool) -> str:
    if not week_signal:
        return "发布时间不在本周区间内，缺少进入本周重点事件的时间依据。"
    if item.source_type == "paper":
        return "该研究在本周样本中属于高相关的新近论文，可作为本周技术储备信号。"
    if item.source_type == "official":
        return "该条目发布时间落在本周内，且来自官方来源，具备作为周内动态观察对象的价值。"
    return "该内容发布时间在本周内，且与重点跟踪主题直接相关。"


def _inclusion_reason(item: ScoredItem, include: bool, report_content_type: str, week_signal: bool) -> str:
    if include:
        return "本周新增、高相关且具备判断价值，适合进入周报正文。"
    if report_content_type in {"resource", "podcast"}:
        return f"该内容更像{report_content_type}页面，不构成周内重点事件。"
    if not week_signal:
        return "与主题相关，但不属于本周新增信号，应作为背景材料而非本周重点。"
    return "虽然有一定相关性，但判断价值不足，建议保留在候选池。"


def _analyst_note(item: ScoredItem, report_content_type: str, include: bool, week_signal: bool) -> str:
    if report_content_type == "paper" and not week_signal:
        return "这是相关论文，但不是本周新增，更适合作为背景参考而不是周内主事件。"
    if report_content_type == "resource":
        return "这是站点资源或栏目页，应在页面类型过滤阶段剔除。"
    if report_content_type == "podcast":
        return "这是节目/播客页，本身不构成行业周报核心事件。"
    if include:
        return "可进入周报正文，但需要在生成阶段明确说明为什么是本周值得看。"
    if not week_signal:
        return "缺少本周增量依据，不建议写入本周重点事件。"
    return "建议保留为候选素材卡片，暂不进入正文。"


def _prompt_for_item(item: ScoredItem) -> str:
    if item.source_type == "official":
        return OFFICIAL_ANALYSIS_PROMPT
    if item.source_type == "paper":
        return PAPER_ANALYSIS_PROMPT
    if item.source_type in {"forum"}:
        return FORUM_ANALYSIS_PROMPT
    if item.source_type in {"news", "company", "blog"}:
        return NEWS_ANALYSIS_PROMPT
    return ANALYSIS_PROMPT
