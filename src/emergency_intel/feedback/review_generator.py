from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List

from emergency_intel.models import ScoredItem
from emergency_intel.utils import ensure_dir
from emergency_intel.feedback.html_renderer import render_review_html


def generate_review_file(
    screened_items: List[ScoredItem],
    reference_date: date | None = None,
    feedback_dir: Path | None = None,
) -> Path:
    """
    Generate a human-readable Markdown review file for weekly feedback annotation.

    Format:
        data/feedback/YYYY-WXX-review.md

    Usage after generation:
        - Mark included items [wrong] if they should NOT have been included
        - Mark excluded items [should] if they SHOULD have been included
        - Leave [ok] / [skip] (or blank) to confirm the pipeline's decision
    """
    from emergency_intel.config import DATA_DIR

    ref = reference_date or date.today()
    iso = ref.isocalendar()
    week_label = f"{iso[0]}-W{iso[1]:02d}"

    out_dir = feedback_dir or (DATA_DIR / "feedback")
    ensure_dir(out_dir)
    out_path = out_dir / f"{week_label}-review.md"

    included = sorted(
        [item for item in screened_items if item.include_in_top_report],
        key=lambda x: x.final_score,
        reverse=True,
    )
    excluded_this_week = sorted(
        [
            item
            for item in screened_items
            if not item.include_in_top_report and item.is_this_week_signal and item.final_score >= 4.0
        ],
        key=lambda x: x.final_score,
        reverse=True,
    )

    lines = [
        f"# 周报反馈审阅 — {week_label}",
        "",
        "## 使用说明",
        "",
        "标记规则：",
        "- 已入报条目：改为 `[wrong]` 表示「不该入选」；保留 `[ok]` 或留空表示认可",
        "- 被排除条目：改为 `[should]` 表示「应该入选」；保留 `[skip]` 或留空表示认可",
        "- 可在「补充意见」区块写自由文字，下次运行会被 Feedback Agent 读取",
        "",
        "---",
        "",
        f"## 已入报（{len(included)} 条）",
        "",
    ]

    if included:
        for item in included:
            domain = ", ".join(item.domain_tags) if item.domain_tags else item.source_type
            lines.append(
                f"- [ok] {item.final_score:.1f} | {item.title} | {domain} | {item.source_name}"
            )
    else:
        lines.append("（本期无入报条目）")

    lines += [
        "",
        f"## 被排除但本周相关（评分 ≥ 4.0，共 {len(excluded_this_week)} 条）",
        "（检查是否有遗漏；如认为应入选，改 `[skip]` 为 `[should]`）",
        "",
    ]

    if excluded_this_week:
        for item in excluded_this_week[:30]:
            domain = ", ".join(item.domain_tags) if item.domain_tags else item.source_type
            lines.append(
                f"- [skip] {item.final_score:.1f} | {item.title} | {domain} | {item.source_name}"
            )
    else:
        lines.append("（无符合条件的排除条目）")

    lines += [
        "",
        "---",
        "",
        "## 补充意见",
        "",
        "（在此写本期整体反馈，例如：某领域内容太少/太多、某信源质量差、筛选方向需调整等）",
        "",
        "",
    ]

    out_path.write_text("\n".join(lines), encoding="utf-8")

    # Generate interactive HTML review page alongside the markdown
    html_path = out_path.with_suffix(".html")
    render_review_html(included, excluded_this_week, week_label, html_path)
    print(f"[反馈] 审阅页面已生成：{html_path}", flush=True)

    return out_path
