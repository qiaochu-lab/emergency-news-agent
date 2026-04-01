"""Generate a single-file static HTML report from a WeeklyReport."""
from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, List

from emergency_intel.models import AnalyzedItem, WeeklyReport
from emergency_intel.report.service import (
    DOMAIN_NAMES_ZH,
    DOMAINS,
    SOURCE_TYPE_ZH,
    _format_domains,
    _get_clean_innovation,
    _get_clean_summary,
    _get_decision_relevance,
    _get_follow_up_items,
    _report_rating,
    _risk_lines,
    _section_summary,
    _short_date,
    _simple_judgment,
)
from emergency_intel.utils import ensure_dir

# ──────────────────────────────────────────────
# CSS + JS template
# ──────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #f5f6fa; color: #1a1a2e; font-size: 15px; line-height: 1.7;
}
a { color: #4a6fa5; text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Nav ── */
nav {
  position: sticky; top: 0; z-index: 100;
  background: #1a1a2e; color: #fff;
  display: flex; align-items: center; gap: 0; padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,.3);
}
nav .brand { font-weight: 700; font-size: 16px; padding: 14px 20px 14px 0; white-space: nowrap; }
nav .nav-links { display: flex; flex-wrap: wrap; gap: 4px; }
nav .nav-links a {
  color: #b0c4de; font-size: 13px; padding: 8px 12px; border-radius: 4px; white-space: nowrap;
}
nav .nav-links a:hover { color: #fff; background: rgba(255,255,255,.1); text-decoration: none; }

/* ── Layout ── */
.container { max-width: 960px; margin: 0 auto; padding: 24px 16px 60px; }

/* ── Cover card ── */
.cover-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 60%, #0f3460 100%);
  color: #fff; border-radius: 12px; padding: 36px 32px; margin-bottom: 28px;
}
.cover-card h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
.cover-card .week { font-size: 15px; opacity: .8; margin-bottom: 20px; }
.cover-meta { display: flex; flex-wrap: wrap; gap: 12px; }
.cover-meta .badge {
  background: rgba(255,255,255,.12); border-radius: 6px; padding: 6px 14px; font-size: 13px;
}
.cover-meta .badge strong { display: block; font-size: 11px; opacity: .7; margin-bottom: 2px; }

/* ── Section ── */
.section { background: #fff; border-radius: 10px; margin-bottom: 20px; overflow: hidden;
           box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; cursor: pointer; user-select: none;
  border-bottom: 1px solid #f0f0f0;
}
.section-header:hover { background: #fafbff; }
.section-header h2 { font-size: 17px; font-weight: 600; }
.section-header .toggle { font-size: 20px; color: #888; transition: transform .2s; }
.section-header.open .toggle { transform: rotate(180deg); }
.section-body { padding: 0 20px 20px; display: none; }
.section-body.open { display: block; }

/* ── Summary table ── */
.summary-table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
.summary-table th, .summary-table td { padding: 9px 14px; border: 1px solid #e8e8e8; text-align: left; }
.summary-table th { background: #f5f6fa; font-weight: 600; width: 30%; }

/* ── Signal dist table ── */
.dist-table { width: 100%; border-collapse: collapse; font-size: 13px; margin: 12px 0; }
.dist-table th { background: #f5f6fa; padding: 8px 12px; text-align: left; border-bottom: 2px solid #dde; font-size: 12px; }
.dist-table td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
.strength-strong { color: #27ae60; font-weight: 600; }
.strength-mid { color: #e67e22; }
.strength-weak { color: #bbb; }

/* ── Featured card ── */
.featured-card {
  border: 1px solid #e8ecf5; border-radius: 8px; overflow: hidden; margin: 16px 0;
  border-left: 4px solid #4a6fa5;
}
.featured-card .fc-thumbnail {
  width: 100%; max-height: 200px; object-fit: cover; display: block;
  border-bottom: 1px solid #e8ecf5;
}
.featured-card .fc-body { padding: 20px; }
.featured-card .fc-meta { font-size: 12px; color: #888; margin-bottom: 12px; display: flex; gap: 12px; flex-wrap: wrap; }
.featured-card .fc-meta span { background: #f0f4ff; padding: 3px 8px; border-radius: 12px; }
.featured-card h3 { font-size: 15px; font-weight: 600; margin-bottom: 10px; line-height: 1.5; }
.featured-card .section-label { font-size: 12px; font-weight: 700; color: #4a6fa5; text-transform: uppercase;
  letter-spacing: .5px; margin: 14px 0 6px; }
.featured-card p { font-size: 14px; color: #333; margin-bottom: 8px; }
.key-points { padding-left: 20px; margin: 6px 0; }
.key-points li { font-size: 14px; color: #333; margin-bottom: 4px; }
.follow-up-list { padding-left: 20px; }
.follow-up-list li { font-size: 13px; color: #555; margin-bottom: 3px; }
.source-link { display: inline-block; margin-top: 10px; font-size: 13px;
  background: #f0f4ff; padding: 4px 12px; border-radius: 4px; }

/* ── Domain item list ── */
.domain-item { border-bottom: 1px solid #f5f5f5; padding: 14px 0; }
.domain-item:last-child { border-bottom: none; }
.domain-item .di-title { font-size: 14px; font-weight: 600; margin-bottom: 4px; line-height: 1.5; }
.domain-item .di-summary { font-size: 13px; color: #555; margin-bottom: 6px; }
.domain-item .di-meta { font-size: 12px; color: #999; }
.domain-tag { display: inline-block; background: #eef3ff; color: #4a6fa5;
  padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-right: 4px; }

/* ── Calendar table ── */
.cal-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
.cal-table th { background: #f5f6fa; padding: 8px 12px; text-align: left; border-bottom: 2px solid #dde; font-size: 12px; }
.cal-table td { padding: 9px 12px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }

/* ── Risk / recommendation lists ── */
.rec-list, .risk-list { padding-left: 20px; margin: 10px 0; }
.rec-list li { color: #333; margin-bottom: 6px; font-size: 14px; }
.risk-list li { color: #c0392b; margin-bottom: 6px; font-size: 14px; }

/* ── Appendix table ── */
.appendix-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.appendix-table th { background: #f5f6fa; padding: 8px 12px; text-align: left;
  border-bottom: 2px solid #dde; font-size: 12px; }
.appendix-table td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }

/* ── Insights ── */
.insight-item { background: #f8f9ff; border-left: 3px solid #4a6fa5;
  padding: 10px 14px; margin: 8px 0; border-radius: 0 6px 6px 0; font-size: 14px; }

/* ── Responsive ── */
@media (max-width: 600px) {
  nav .nav-links a { font-size: 11px; padding: 6px 8px; }
  .cover-card { padding: 24px 16px; }
  .cover-card h1 { font-size: 20px; }
}
"""

_JS = """
document.querySelectorAll('.section-header').forEach(function(header) {
  header.addEventListener('click', function() {
    var body = header.nextElementSibling;
    var isOpen = body.classList.contains('open');
    body.classList.toggle('open', !isOpen);
    header.classList.toggle('open', !isOpen);
  });
});
// Open first section by default
var first = document.querySelector('.section-body');
if (first) {
  first.classList.add('open');
  first.previousElementSibling.classList.add('open');
}
"""


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────

def render_report_html(report: WeeklyReport, output_path: Path) -> str:
    ensure_dir(output_path.parent)
    rating = _report_rating(report)

    domain_groups: Dict[str, List[AnalyzedItem]] = {}
    for domain in DOMAINS:
        domain_groups[domain] = []
    for item in report.selected_items:
        for tag in item.domain_tags:
            if tag in DOMAINS:
                domain_groups[tag].append(item)

    # Deduplicate across domain sections (same rule as markdown renderer)
    chapter3_seen: set = set()

    body_parts: List[str] = []

    # Cover
    body_parts.append(_render_cover(report, rating))

    # Section 1: 执行摘要 (open by default via JS)
    body_parts.append(_render_section(
        "exec-summary", "执行摘要",
        _render_exec_summary(report, rating),
        open_default=True,
    ))

    # Section 2: 本周概览
    body_parts.append(_render_section(
        "overview", "一、本周概览",
        _render_overview(report, domain_groups),
    ))

    # Section 3: 重点事件
    body_parts.append(_render_section(
        "featured", "二、重点事件深度分析",
        _render_featured(report),
    ))

    # Section 4: 各领域动态
    body_parts.append(_render_section(
        "domains", "三、各领域精选动态",
        _render_domains(domain_groups, chapter3_seen),
    ))

    # Section 5: 事件日历
    body_parts.append(_render_section(
        "calendar", "四、事件日历",
        _render_calendar(report),
    ))

    # Section 6: 建议与风险
    body_parts.append(_render_section(
        "recs", "五、建议与风险",
        _render_recommendations(report),
    ))

    # Section 7: 附录
    body_parts.append(_render_section(
        "appendix", "附录：本期信源列表",
        _render_appendix(report),
    ))

    nav_html = _render_nav(report)
    page_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>泛应急技术行业周报 {report.week_range}</title>
<style>{_CSS}</style>
</head>
<body>
{nav_html}
<div class="container">
{''.join(body_parts)}
</div>
<script>{_JS}</script>
</body>
</html>"""

    with output_path.open("w", encoding="utf-8") as fh:
        fh.write(page_html)
    return page_html


# ──────────────────────────────────────────────
# Render helpers
# ──────────────────────────────────────────────

def _e(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text or ""))


def _render_nav(report: WeeklyReport) -> str:
    links = [
        ("#exec-summary", "执行摘要"),
        ("#overview", "本周概览"),
        ("#featured", "重点事件"),
        ("#domains", "各领域动态"),
        ("#calendar", "事件日历"),
        ("#recs", "建议与风险"),
        ("#appendix", "信源附录"),
    ]
    links_html = "".join(f'<a href="{href}">{_e(label)}</a>' for href, label in links)
    week = report.week_range.replace(" to ", " — ")
    return f"""<nav>
  <span class="brand">泛应急周报 · {_e(week)}</span>
  <div class="nav-links">{links_html}</div>
</nav>"""


def _render_section(anchor: str, title: str, inner_html: str, open_default: bool = False) -> str:
    open_cls = " open" if open_default else ""
    return f"""<div class="section" id="{anchor}">
  <div class="section-header{open_cls}">
    <h2>{_e(title)}</h2>
    <span class="toggle">▾</span>
  </div>
  <div class="section-body{open_cls}">{inner_html}</div>
</div>"""


def _render_cover(report: WeeklyReport, rating: str) -> str:
    week = report.week_range.replace(" to ", " — ").replace("-", ".")
    generated = report.generated_at[:16].replace("T", " ")
    count = len(report.selected_items)
    return f"""<div class="cover-card">
  <h1>泛应急技术行业周报</h1>
  <div class="week">{_e(week)}</div>
  <div class="cover-meta">
    <div class="badge"><strong>研报评级</strong>{_e(rating)}</div>
    <div class="badge"><strong>覆盖领域</strong>AI · 无人机 · 通信网络 · 泛应急</div>
    <div class="badge"><strong>本期信号数</strong>{count} 条</div>
    <div class="badge"><strong>生成时间</strong>{_e(generated)}</div>
  </div>
</div>"""


def _render_exec_summary(report: WeeklyReport, rating: str) -> str:
    top = report.selected_items[0] if report.selected_items else None
    top_title = (top.title[:40] + "...") if top and len(top.title) > 40 else (top.title if top else "—")
    insight = report.weekly_insights[0] if report.weekly_insights else "本周主线以高确定性事件驱动为主"
    risk = _risk_lines(report)[0] if report.selected_items else "信源样本不足，建议扩充采集范围"

    rows = [
        ("景气度", _market_summary_short(report)),
        ("核心主线", insight),
        ("重点事件", top_title),
        ("风险提示", risk),
    ]
    rows_html = "".join(
        f"<tr><th>{_e(k)}</th><td>{_e(v)}</td></tr>" for k, v in rows
    )
    market = _market_summary(report)
    return f"""<table class="summary-table">{rows_html}</table>
<p style="margin-top:12px;font-size:14px;color:#555">{_e(market)}</p>"""


def _render_overview(report: WeeklyReport, domain_groups: Dict[str, List[AnalyzedItem]]) -> str:
    parts: List[str] = []

    # 1.1 行业整体表现
    market = _market_summary(report)
    bullets = _market_supporting_lines(report)
    bullets_html = "".join(f"<li>{_e(b)}</li>" for b in bullets)
    parts.append(f"""<h3 style="margin:16px 0 8px;font-size:15px">1.1 行业整体表现</h3>
<p style="font-size:14px;color:#333;margin-bottom:8px">{_e(market)}</p>
<ul style="padding-left:20px;font-size:14px;color:#555">{bullets_html}</ul>""")

    # 1.2 信号分布
    dist_rows = ""
    for domain in DOMAINS:
        items = domain_groups.get(domain, [])
        count = len(items)
        if count >= 3:
            strength, cls = "强", "strength-strong"
        elif count >= 1:
            strength, cls = "中", "strength-mid"
        else:
            strength, cls = "弱", "strength-weak"
        rep = items[0].title if items else "—"
        rep_short = (rep[:28] + "...") if len(rep) > 28 else rep
        name = DOMAIN_NAMES_ZH[domain]
        dist_rows += f"<tr><td>{_e(name)}</td><td>{count}</td><td class='{cls}'>{strength}</td><td>{_e(rep_short)}</td></tr>"

    parts.append(f"""<h3 style="margin:20px 0 8px;font-size:15px">1.2 各领域信号分布</h3>
<table class="dist-table">
  <tr><th>领域</th><th>信号数</th><th>强弱</th><th>代表性事件</th></tr>
  {dist_rows}
</table>""")

    # 1.3 重点主体动态
    items_5 = report.selected_items[:5]
    items_html = ""
    for item in items_5:
        judgment = _simple_judgment(item)
        items_html += f"""<div class="domain-item">
  <div class="di-title">{_e(item.title)} <span style="font-size:12px;color:#888">（{_e(item.source_name)}）</span></div>
  <div class="di-summary">{_e(judgment)}</div>
</div>"""

    parts.append(f"""<h3 style="margin:20px 0 8px;font-size:15px">1.3 重点主体动态</h3>
{items_html if items_html else '<p style="color:#888;font-size:14px">暂无代表性主体进入重点观察名单。</p>'}""")

    return "\n".join(parts)


def _render_featured(report: WeeklyReport) -> str:
    from emergency_intel.report.service import _select_balanced_featured, MAX_FEATURED_ITEMS
    featured = _select_balanced_featured(report.selected_items, MAX_FEATURED_ITEMS)
    if not featured:
        return '<p style="color:#888;font-size:14px;padding:16px 0">本周进入主体报告的高信号事件数量有限。</p>'

    cards: List[str] = []
    for idx, item in enumerate(featured, 1):
        date_str = _short_date(item.published_at)
        domain_str = _format_domains(item.domain_tags)
        summary_text = _get_clean_summary(item)
        innovation_text = _get_clean_innovation(item)
        decision_text = _get_decision_relevance(item)
        follow_up_items = _get_follow_up_items(item)

        kp_html = ""
        if item.key_points:
            kp_items = "".join(f"<li>{_e(str(kp))}</li>" for kp in item.key_points[:4] if kp)
            kp_html = f'<div class="section-label">核心要点</div><ul class="key-points">{kp_items}</ul>'

        innovation_html = f'<div class="section-label">分析判断</div><p>{_e(innovation_text)}</p>' if innovation_text else ""
        decision_html = f'<div class="section-label">决策启示</div><p>{_e(decision_text)}</p>' if decision_text else ""

        fu_html = ""
        if follow_up_items:
            fu_items = "".join(f"<li>{_e(tip)}</li>" for tip in follow_up_items)
            fu_html = f'<div class="section-label">跟踪建议</div><ul class="follow-up-list">{fu_items}</ul>'

        link_html = ""
        if item.url:
            link_html = f'<a class="source-link" href="{_e(item.url)}" target="_blank" rel="noopener">→ 原文链接</a>'

        thumbnail_url = getattr(item, "thumbnail_url", "") or ""
        thumb_html = (
            f'<img class="fc-thumbnail" src="{_e(thumbnail_url)}" alt="" loading="lazy" '
            f'onerror="this.style.display=\'none\'">'
            if thumbnail_url else ""
        )

        cards.append(f"""<div class="featured-card">
  {thumb_html}
  <div class="fc-body">
  <div class="fc-meta">
    <span>来源：{_e(item.source_name)}</span>
    <span>日期：{_e(date_str)}</span>
    <span>领域：{_e(domain_str)}</span>
  </div>
  <h3>{idx}. {_e(item.title)}</h3>
  <div class="section-label">事件概述</div>
  <p>{_e(summary_text)}</p>
  {kp_html}
  {innovation_html}
  {decision_html}
  {fu_html}
  {link_html}
  </div>
</div>""")

    return "\n".join(cards)


def _render_domains(domain_groups: Dict[str, List[AnalyzedItem]], seen_ids: set) -> str:
    parts: List[str] = []
    for sec_idx, domain in enumerate(DOMAINS, 1):
        name = DOMAIN_NAMES_ZH[domain]
        all_items = domain_groups.get(domain, [])
        unique_items = [it for it in all_items if it.id not in seen_ids]

        parts.append(f'<h3 style="margin:20px 0 10px;font-size:15px;border-left:3px solid #4a6fa5;padding-left:10px">{sec_idx}. {_e(name)}</h3>')

        if not unique_items:
            from emergency_intel.report.service import DOMAIN_EMPTY_SUMMARIES
            parts.append(f'<p style="color:#888;font-size:13px;padding:0 0 12px">{_e(DOMAIN_EMPTY_SUMMARIES[domain])}</p>')
            continue

        domain_items = unique_items[:10]
        for it in domain_items:
            seen_ids.add(it.id)

        parts.append(f'<p style="font-size:13px;color:#888;margin-bottom:10px">精选本周高信号事件（共 {len(domain_items)} 条）</p>')
        items_html = ""
        for item in domain_items:
            summary = _get_clean_summary(item)
            short_summary = (summary[:150] + "...") if len(summary) > 150 else summary
            date_str = _short_date(item.published_at)
            title_html = f'<a href="{_e(item.url)}" target="_blank" rel="noopener">{_e(item.title)}</a>' if item.url else _e(item.title)
            items_html += f"""<div class="domain-item">
  <div class="di-title">{title_html}</div>
  <div class="di-summary">{_e(short_summary)}</div>
  <div class="di-meta">{_e(item.source_name)} | {_e(date_str)}</div>
</div>"""
        parts.append(items_html)

    return "\n".join(parts)


def _render_calendar(report: WeeklyReport) -> str:
    if not report.selected_items:
        return '<p style="color:#888;font-size:14px;padding:16px 0">本周重要事件相对有限。</p>'

    rows = ""
    for item in report.selected_items[:8]:
        date_str = _short_date(item.published_at)
        short_title = (item.title[:32] + "...") if len(item.title) > 32 else item.title
        judgment = _simple_judgment(item)
        short_j = (judgment[:45] + "...") if len(judgment) > 45 else judgment
        title_html = f'<a href="{_e(item.url)}" target="_blank" rel="noopener">{_e(short_title)}</a>' if item.url else _e(short_title)
        rows += f"<tr><td>{_e(date_str)}</td><td>{title_html}</td><td>{_e(item.source_name)}</td><td>{_e(short_j)}</td></tr>"

    return f"""<h3 style="margin:16px 0 8px;font-size:15px">本周重要事件</h3>
<table class="cal-table">
  <tr><th>日期</th><th>事件标题</th><th>来源</th><th>要点</th></tr>
  {rows}
</table>"""


def _render_recommendations(report: WeeklyReport) -> str:
    from emergency_intel.report.service import _focus_directions
    recs = _focus_directions(report)
    risks = _risk_lines(report)
    rec_items = "".join(f"<li>{_e(r)}</li>" for r in recs)
    risk_items = "".join(f"<li>{_e(r)}</li>" for r in risks)
    return f"""<h3 style="margin:16px 0 8px;font-size:15px">建议关注方向</h3>
<ul class="rec-list">{rec_items}</ul>
<h3 style="margin:20px 0 8px;font-size:15px">风险提示</h3>
<ul class="risk-list">{risk_items}</ul>"""


def _render_appendix(report: WeeklyReport) -> str:
    if not report.selected_items:
        return '<p style="color:#888;font-size:14px">本期暂无来源记录。</p>'

    from collections import Counter
    seen_sources: dict = {}
    for item in report.selected_items:
        if item.source_name not in seen_sources:
            seen_sources[item.source_name] = item
    source_count = Counter(item.source_name for item in report.selected_items)

    rows = ""
    for idx, (source_name, rep_item) in enumerate(seen_sources.items(), 1):
        type_zh = SOURCE_TYPE_ZH.get(rep_item.source_type, rep_item.source_type)
        domain_tags = sorted({
            tag for item in report.selected_items
            if item.source_name == source_name
            for tag in item.domain_tags
        })
        domain_zh = "、".join(DOMAIN_NAMES_ZH.get(d, d) for d in domain_tags[:2])
        count = source_count[source_name]
        link = f'<a href="{_e(rep_item.url)}" target="_blank" rel="noopener">链接</a>' if rep_item.url else "—"
        rows += f"<tr><td>{idx}</td><td>{_e(source_name)}</td><td>{_e(type_zh)}</td><td>{_e(domain_zh)}</td><td>{count}</td><td>{link}</td></tr>"

    return f"""<table class="appendix-table">
  <tr><th>#</th><th>来源名称</th><th>类型</th><th>领域</th><th>本期条目数</th><th>代表链接</th></tr>
  {rows}
</table>"""


# ──────────────────────────────────────────────
# Reuse helpers from service (avoid circular deps by importing at call site)
# ──────────────────────────────────────────────

def _market_summary(report: WeeklyReport) -> str:
    from emergency_intel.report.service import _market_summary as _ms
    return _ms(report)


def _market_summary_short(report: WeeklyReport) -> str:
    from emergency_intel.report.service import _market_summary_short as _mss
    return _mss(report)


def _market_supporting_lines(report: WeeklyReport) -> List[str]:
    from emergency_intel.report.service import _market_supporting_lines as _msl
    return _msl(report)
