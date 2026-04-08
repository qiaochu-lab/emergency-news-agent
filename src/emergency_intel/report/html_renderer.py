"""Generate a single-file static HTML report from a WeeklyReport."""
from __future__ import annotations

import html
import os
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
/* ── Reset & Variables ── */
:root {
  --bg-color: #f5f6fa;
  --text-color: #1a1a2e;
  --card-bg: #fff;
  --card-border: #e8ecf5;
  --primary: #4a6fa5;
  --nav-bg: #1a1a2e;
  --nav-text: #fff;
  --th-bg: #f5f6fa;
  --border-color: #e8e8e8;
  --muted-text: #555;
}
.dark-mode {
  --bg-color: #0f172a;
  --text-color: #e2e8f0;
  --card-bg: #1e293b;
  --card-border: #334155;
  --primary: #60a5fa;
  --nav-bg: #020617;
  --nav-text: #e2e8f0;
  --th-bg: #0f172a;
  --border-color: #334155;
  --muted-text: #94a3b8;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--bg-color); color: var(--text-color); font-size: 15px; line-height: 1.7;
  transition: background-color 0.3s, color 0.3s;
}
a { color: var(--primary); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── Nav ── */
nav {
  position: sticky; top: 0; z-index: 100;
  background: var(--nav-bg); color: var(--nav-text);
  display: flex; align-items: center; padding: 0 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,.3);
  flex-wrap: wrap; justify-content: space-between;
}
.nav-left { display: flex; align-items: center; }
nav .brand { font-weight: 700; font-size: 16px; padding: 14px 20px 14px 0; white-space: nowrap; }
nav .nav-links { display: flex; flex-wrap: wrap; gap: 4px; }
nav .nav-links a { color: #b0c4de; font-size: 13px; padding: 8px 12px; border-radius: 4px; white-space: nowrap; }
nav .nav-links a:hover { color: #fff; background: rgba(255,255,255,.1); text-decoration: none; }
.nav-actions button { background: rgba(255,255,255,0.15); color: #fff; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 12px; transition: 0.2s; margin-left: 8px;}
.nav-actions button:hover { background: rgba(255,255,255,0.3); }

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
.cover-meta .badge { background: rgba(255,255,255,.12); border-radius: 6px; padding: 6px 14px; font-size: 13px; }
.cover-meta .badge strong { display: block; font-size: 11px; opacity: .7; margin-bottom: 2px; }

/* ── Section ── */
.section { background: var(--card-bg); border-radius: 10px; margin-bottom: 20px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08); border: 1px solid var(--border-color); }
.section-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; cursor: pointer; user-select: none; border-bottom: 1px solid var(--border-color); }
.section-header:hover { background: rgba(128,128,128,0.05); }
.section-header h2 { font-size: 17px; font-weight: 600; }
.section-header .toggle { font-size: 20px; color: #888; transition: transform .2s; }
.section-header.open .toggle { transform: rotate(180deg); }
.section-body { padding: 0 20px 20px; display: none; }
.section-body.open { display: block; }

/* ── Tables ── */
table { width: 100%; border-collapse: collapse; font-size: 14px; color: var(--text-color); }
th { background: var(--th-bg); padding: 9px 14px; border: 1px solid var(--border-color); text-align: left; }
td { padding: 9px 14px; border: 1px solid var(--border-color); }

/* ── Featured card splitting facts/analysis ── */
.featured-card {
  border: 1px solid var(--card-border); border-radius: 8px; overflow: hidden; margin: 16px 0;
  border-left: 4px solid var(--primary); display: flex; flex-direction: column;
}
.featured-header { padding: 16px 20px; border-bottom: 1px solid var(--border-color); }
.featured-header h3 { font-size: 16px; font-weight: 600; margin-bottom: 8px; }
.fc-meta { font-size: 12px; color: var(--muted-text); display: flex; gap: 12px; flex-wrap: wrap; }
.fc-meta span { background: rgba(128,128,128,0.1); padding: 3px 8px; border-radius: 12px; }

.featured-content { display: flex; flex-direction: column; }
.fc-left, .fc-right { padding: 20px 24px; }
.fc-left { background: rgba(128,128,128,0.02); border-bottom: 1px solid var(--border-color); }

.section-label { font-size: 11px; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: .5px; margin: 14px 0 6px; }
.key-facts { padding-left: 0; list-style: none; display: flex; flex-wrap: wrap; gap: 6px; }
.key-facts li { font-size: 12px; border: 1px solid var(--border-color); border-radius: 4px; padding: 2px 8px; background: rgba(128,128,128,0.05); }

/* Tooltip for Glossary */
.glossary-tooltip { position: relative; border-bottom: 1px dashed var(--primary); cursor: help; color: var(--primary); }
.glossary-tooltip .tooltip-text {
  visibility: hidden; width: 220px; background-color: var(--nav-bg); color: var(--nav-text); text-align: center;
  border-radius: 6px; padding: 8px; position: absolute; z-index: 10; bottom: 125%; left: 50%;
  margin-left: -110px; opacity: 0; transition: opacity 0.3s; font-size: 12px; font-weight: normal; font-family: sans-serif;
  box-shadow: 0 4px 6px rgba(0,0,0,0.3); pointer-events: none;
}
.glossary-tooltip:hover .tooltip-text { visibility: visible; opacity: 1; }

.action-bar { display: flex; gap: 10px; padding: 10px 20px; background: rgba(128,128,128,0.05); border-top: 1px solid var(--border-color); align-items: center; justify-content: flex-end;}
.action-btn { background: none; border: 1px solid var(--border-color); color: var(--text-color); padding: 4px 10px; border-radius: 4px; cursor: pointer; font-size: 12px; }
.action-btn:hover { background: var(--bg-color); }

/* ── Domain items ── */
.domain-item {
  border: 1px solid var(--card-border); border-radius: 8px; padding: 16px 18px;
  margin: 12px 0; background: var(--card-bg);
  border-left: 3px solid var(--primary);
}
.di-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; line-height: 1.5; }
.di-title a { color: var(--primary); }
.di-summary { font-size: 14px; color: var(--text-color); line-height: 1.75; margin-bottom: 10px; }
.di-meta { font-size: 12px; color: var(--muted-text); margin-bottom: 10px; }
.di-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.di-actions .action-btn { font-size: 11px; padding: 3px 8px; }

/* ── Tables ── */
.dist-table td, .cal-table td, .appendix-table td { vertical-align: top; }
.cal-table td:last-child { font-size: 13px; line-height: 1.6; }
.strength-strong { color: #27ae60; font-weight: 600; }
.strength-mid    { color: #e67e22; font-weight: 600; }
.strength-weak   { color: #95a5a6; }
.rec-list, .risk-list { padding-left: 20px; font-size: 14px; line-height: 2; }

@media (max-width: 768px) {
  .fc-left, .fc-right { padding: 16px; }
}
"""

_JS = """
// Auto section open/close
document.querySelectorAll('.section-header').forEach(function(header) {
  header.addEventListener('click', function() {
    var body = header.nextElementSibling;
    var isOpen = body.classList.contains('open');
    body.classList.toggle('open', !isOpen);
    header.classList.toggle('open', !isOpen);
  });
});

// Default open first section
var first = document.querySelector('.section-body');
if (first) {
  first.classList.add('open');
  first.previousElementSibling.classList.add('open');
}

// Dark Mode Toggle
function toggleTheme() {
  document.body.classList.toggle('dark-mode');
  const isDark = document.body.classList.contains('dark-mode');
  localStorage.setItem('theme', isDark ? 'dark' : 'light');
}

// Check saved theme
if (localStorage.getItem('theme') === 'dark') {
  document.body.classList.add('dark-mode');
}

// Global Filter for domains
function filterByDomain(domain) {
  document.querySelectorAll('.featured-card').forEach(function(card) {
    if (domain === 'all' || card.dataset.domain === domain) {
      card.style.display = 'flex';
    } else {
      card.style.display = 'none';
    }
  });
}

// Copy Summary Action
function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerText;
    btn.innerText = "已复制 ✓";
    setTimeout(() => { btn.innerText = originalText; }, 2000);
  });
}

// ── GitHub Feedback ──────────────────────────────────────────
// 反馈通过 GitHub Issues API 写入仓库，pipeline 下次读取后更新权重。
const GITHUB_REPO  = "qiaochu-lab/emergency-news-agent";
const GITHUB_TOKEN = "{github_token_placeholder}";

function sendFeedback(itemId, feedbackType, btn) {
  const originalText = btn.innerText;
  btn.innerText = "提交中...";
  btn.disabled = true;

  const label    = feedbackType === 'interested' ? '⭐ 感兴趣' : '🥱 不感兴趣';
  const emoji    = feedbackType === 'interested' ? '⭐' : '🥱';
  const title    = `[feedback] ${emoji} ${itemId.slice(0,40)}`;
  const body     = `**反馈类型**: ${label}\n**条目ID**: ${itemId}\n**时间**: ${new Date().toISOString()}\n**来自**: 周报页面`;

  fetch(`https://api.github.com/repos/${GITHUB_REPO}/issues`, {
    method: 'POST',
    headers: {
      'Authorization': `token ${GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
      'Accept': 'application/vnd.github.v3+json'
    },
    body: JSON.stringify({
      title: title,
      body: body,
      labels: ['feedback', feedbackType]
    })
  })
  .then(res => {
    if (res.ok) {
      btn.innerText = label + " ✓";
      btn.style.borderColor = feedbackType === 'interested' ? '#27ae60' : '#e74c3c';
    } else {
      res.json().then(j => console.error('GitHub API error:', j));
      btn.innerText = "失败，见控制台";
      btn.disabled = false;
    }
  })
  .catch(err => {
    console.error('Feedback error:', err);
    btn.innerText = originalText;
    btn.disabled = false;
  });
}
"""


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────

def render_report_html(report: WeeklyReport, output_path: Path) -> str:
    ensure_dir(output_path.parent)
    rating = _report_rating(report)

    domain_groups: Dict[str, List[AnalyzedItem]] = {d: [] for d in DOMAINS}
    for item in report.selected_items:
        primary = next((tag for tag in item.domain_tags if tag in DOMAINS), None)
        if primary:
            domain_groups[primary].append(item)

    # Deduplicate across domain sections (same rule as markdown renderer)
    chapter3_seen: set = set()

    _ZH_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
    _sec_idx = 0

    def _next_title(label: str) -> str:
        nonlocal _sec_idx
        n = _ZH_NUM[_sec_idx] if _sec_idx < len(_ZH_NUM) else str(_sec_idx + 1)
        _sec_idx += 1
        return f"{n}、{label}"

    body_parts: List[str] = []

    # Cover
    body_parts.append(_render_cover(report, rating))

    body_parts.append(_render_section(
        "overview", _next_title("本周概览"),
        _render_overview(report, domain_groups),
    ))

    body_parts.append(_render_section(
        "featured", _next_title("重点事件深度分析"),
        _render_featured(report),
    ))

    body_parts.append(_render_section(
        "domains", _next_title("各领域精选动态"),
        _render_domains(domain_groups, chapter3_seen),
    ))

    # 精选博客/播客（仅有内容时显示）
    transcript_html = _render_transcripts(report)
    if transcript_html:
        body_parts.append(_render_section(
            "transcripts", _next_title("本周精选博客/播客"),
            transcript_html,
        ))

    # X平台热议（仅有内容时显示）
    x_feed_html = _render_x_feed(report)
    if x_feed_html:
        body_parts.append(_render_section(
            "x-feed", _next_title("本周X平台热议"),
            x_feed_html,
        ))

    body_parts.append(_render_section(
        "calendar", _next_title("事件日历"),
        _render_calendar(report),
    ))

    body_parts.append(_render_section(
        "recs", _next_title("建议与风险"),
        _render_recommendations(report),
    ))

    body_parts.append(_render_section(
        "appendix", "附录：信源与采集统计",
        _render_appendix(report),
    ))

    nav_html = _render_nav(report, output_path)
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

    # Inject GitHub token from env at generation time (keeps source code clean)
    github_token = os.environ.get("GITHUB_TOKEN", "")
    page_html = page_html.replace("{github_token_placeholder}", github_token)

    with output_path.open("w", encoding="utf-8") as fh:
        fh.write(page_html)
    return page_html


def render_index_html(outputs_dir: Path) -> None:
    """Regenerate outputs_dir/index.html listing all report editions."""
    ensure_dir(outputs_dir)
    files = sorted(
        outputs_dir.glob("应急周报_*.html"),
        key=lambda p: p.stat().st_mtime,
    )

    rows = ""
    for idx, f in enumerate(files, 1):
        # Extract week label from filename: 应急周报_2026-W14_20260403-120000.html
        stem = f.stem  # e.g. 应急周报_2026-W14_20260403-120000
        parts = stem.split("_", 2)
        week_label = parts[1] if len(parts) >= 2 else stem
        raw_ts = parts[2] if len(parts) >= 3 else ""
        # Format 20260403-120000 → 2026-04-03 12:00
        if len(raw_ts) >= 8 and raw_ts[:8].isdigit():
            d = raw_ts[:8]
            ts_label = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            t = raw_ts[9:13] if len(raw_ts) >= 13 else raw_ts[9:]
            if len(t) >= 4:
                ts_label += f" {t[:2]}:{t[2:4]}"
        else:
            ts_label = raw_ts
        rows += (
            f'<tr><td style="text-align:center">{idx}</td>'
            f'<td><a href="{_e(f.name)}">{_e(week_label)}</a></td>'
            f'<td style="color:#888;font-size:13px">{_e(ts_label)}</td></tr>\n'
        )

    if not rows:
        rows = '<tr><td colspan="3" style="color:#888;text-align:center">暂无报告</td></tr>'

    index_css = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
       background: #f5f6fa; color: #1a1a2e; font-size: 15px; line-height: 1.7; }
nav { background: #1a1a2e; color: #fff; padding: 14px 20px; }
nav .brand { font-weight: 700; font-size: 16px; }
.container { max-width: 640px; margin: 40px auto; padding: 0 16px; }
h1 { font-size: 22px; font-weight: 700; margin-bottom: 6px; }
.subtitle { font-size: 14px; color: #888; margin-bottom: 24px; }
table { width: 100%; border-collapse: collapse; background: #fff;
        border-radius: 10px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
th { background: #f5f6fa; padding: 10px 16px; text-align: left;
     border-bottom: 2px solid #dde; font-size: 13px; }
td { padding: 11px 16px; border-bottom: 1px solid #f0f0f0; }
tr:last-child td { border-bottom: none; }
a { color: #4a6fa5; text-decoration: none; }
a:hover { text-decoration: underline; }
"""

    content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>泛应急周报 · 期次列表</title>
<style>{index_css}</style>
</head>
<body>
<nav><span class="brand">泛应急周报</span></nav>
<div class="container">
  <h1>期次列表</h1>
  <p class="subtitle">共 {len(files)} 期报告，点击期次查看详情</p>
  <table>
    <tr><th>#</th><th>期次 / 周</th><th>生成时间</th></tr>
    {rows}
  </table>
</div>
</body>
</html>"""

    index_path = outputs_dir / "index.html"
    with index_path.open("w", encoding="utf-8") as fh:
        fh.write(content)
    print(f"[报告] 期次列表已更新 → {index_path}", flush=True)


# ──────────────────────────────────────────────
# Render helpers
# ──────────────────────────────────────────────

def _e(text: str) -> str:
    """HTML-escape a string."""
    return html.escape(str(text or ""))


def _render_nav(report: WeeklyReport, output_path: Path) -> str:
    links = [
        ("#overview", "本周概览"),
        ("#featured", "重点事件"),
        ("#domains", "各领域动态"),
        ("#calendar", "事件日历"),
        ("#recs", "建议与风险"),
        ("#appendix", "信源附录"),
    ]
    links_html = "".join(f'<a href="{href}">{_e(label)}</a>' for href, label in links)

    return f"""<nav>
  <div class="nav-left">
    <a class="brand" href="index.html" style="color:inherit;text-decoration:none">← 期次列表</a>
    <span class="brand" style="opacity:.4;padding:0 4px">|</span>
    <span class="brand">泛应急周报</span>
    <div class="nav-links">{links_html}</div>
  </div>
  <div class="nav-actions">
    <button onclick="toggleTheme()">🌓 切换主题</button>
  </div>
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

    # 1.3 重点主体动态已移除

    return "\n".join(parts)


def _render_featured(report: WeeklyReport) -> str:
    from emergency_intel.report.service import _select_balanced_featured, MAX_FEATURED_ITEMS
    featured = _select_balanced_featured(report.selected_items, MAX_FEATURED_ITEMS)
    if not featured:
        return '<p style="color:#888;font-size:14px;padding:16px 0">本周进入主体报告的高信号事件数量有限。</p>'

    cards: List[str] = []
    
    # Process text tooltips for glossary logic
    def _apply_tooltips(text: str, glossary: list) -> str:
        for it in glossary:
            term = it.get("term")
            exp = it.get("explanation")
            if term and exp and term in text:
                tooltip_html = f'<span class="glossary-tooltip">{_e(term)}<span class="tooltip-text">{_e(exp)}</span></span>'
                text = text.replace(term, tooltip_html)
        return text

    for idx, item in enumerate(featured, 1):
        date_str = _short_date(item.published_at)
        domain_str = _format_domains(item.domain_tags)
        
        # for filtering classes logic:
        primary_domain = next((tag for tag in item.domain_tags if tag in DOMAINS), "all")
        
        summary_text = _get_clean_summary(item)
        innovation_text = _get_clean_innovation(item)
        decision_text = _get_decision_relevance(item)

        glossary_terms = getattr(item, "glossary_terms", []) or []
        innovation_text = _apply_tooltips(innovation_text, glossary_terms)

        kf_html = ""
        key_facts = getattr(item, "key_facts", []) or []
        if key_facts:
            kf_items = "".join(f"<li>{_e(str(f))}</li>" for f in key_facts[:5] if f)
            kf_html = f'<div class="section-label">关键事实溯源</div><ul class="key-facts">{kf_items}</ul>'

        kp_html = ""
        if item.key_points:
            kp_items = "".join(f"<li>{_apply_tooltips(str(kp), glossary_terms)}</li>" for kp in item.key_points[:4] if kp)
            kp_html = f'<div class="section-label">核心要点</div><ul style="padding-left: 20px;">{kp_items}</ul>'

        innovation_html = f'<div class="section-label">分析判断</div><p>{innovation_text}</p>' if innovation_text else ""
        decision_html = f'<div class="section-label">决策启示</div><p>{_apply_tooltips(decision_text, glossary_terms)}</p>' if decision_text else ""

        link_html = ""
        if item.url:
            link_html = f'<a class="action-btn" href="{_e(item.url)}" target="_blank" rel="noopener">🔗 原始信息源</a>'

        cards.append(f"""<div class="featured-card" data-domain="{_e(primary_domain)}">
  <div class="featured-header">
    <div class="fc-meta">
      <span>来源：{_e(item.source_name)}</span>
      <span>日期：{_e(date_str)}</span>
      <span>领域：{_e(domain_str)}</span>
    </div>
    <h3>{idx}. {_e(item.title_zh or item.title)}</h3>
  </div>
  <div class="featured-content">
    <div class="fc-left">
      <div class="section-label">事件摘要</div>
      <p>{_e(summary_text)}</p>
      {kf_html}
      {kp_html}
    </div>
    <div class="fc-right">
      {innovation_html}
      {decision_html}
    </div>
  </div>
  <div class="action-bar">
    <button class="action-btn" onclick="copyText(this, '{_e(summary_text)}')">📋 复制摘要</button>
    <button class="action-btn" onclick="sendFeedback('{item.id}', 'interested', this)">⭐ 感兴趣</button>
    <button class="action-btn" onclick="sendFeedback('{item.id}', 'not_interested', this)">🥱 不太感冒</button>
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
            date_str = _short_date(item.published_at)
            title_html = f'<a href="{_e(item.url)}" target="_blank" rel="noopener">{_e(item.title)}</a>' if item.url else _e(item.title)
            link_btn = f'<a class="action-btn" href="{_e(item.url)}" target="_blank" rel="noopener">🔗 原文</a>' if item.url else ""
            items_html += f"""<div class="domain-item">
  <div class="di-title">{title_html}</div>
  <div class="di-summary">{_e(summary)}</div>
  <div class="di-meta">{_e(item.source_name)} | {_e(date_str)}</div>
  <div class="di-actions">
    <button class="action-btn" onclick="sendFeedback('{_e(item.id)}', 'interested', this)">⭐ 感兴趣</button>
    <button class="action-btn" onclick="sendFeedback('{_e(item.id)}', 'not_interested', this)">🥱 不太感冒</button>
    {link_btn}
  </div>
</div>"""
        parts.append(items_html)

    return "\n".join(parts)


def _render_calendar(report: WeeklyReport) -> str:
    if not report.selected_items:
        return '<p style="color:#888;font-size:14px;padding:16px 0">本周重要事件相对有限。</p>'

    rows = ""
    for item in report.selected_items:
        date_str = _short_date(item.published_at)
        title_html = f'<a href="{_e(item.url)}" target="_blank" rel="noopener">{_e(item.title)}</a>' if item.url else _e(item.title)
        rows += f"<tr><td style='white-space:nowrap;width:90px'>{_e(date_str)}</td><td>{title_html}</td></tr>"

    return f"""<h3 style="margin:16px 0 8px;font-size:15px">本周重要事件（共 {len(report.selected_items)} 条）</h3>
<table class="cal-table">
  <tr><th style="width:90px">日期</th><th>事件标题</th></tr>
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
    parts: List[str] = []

    # ── Section A: 入报信源 ──
    if report.selected_items:
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

        parts.append(f"""<h3 style="margin:16px 0 10px;font-size:15px">A. 入报信源列表</h3>
<table class="appendix-table">
  <tr><th>#</th><th>来源名称</th><th>类型</th><th>领域</th><th>本期条目数</th><th>代表链接</th></tr>
  {rows}
</table>""")
    else:
        parts.append('<p style="color:#888;font-size:14px">本期暂无来源记录。</p>')

    # ── Section B: 全量采集统计 ──
    if report.source_stats:
        ok_stats = [s for s in report.source_stats if s.get("status") == "ok"]
        err_stats = [s for s in report.source_stats if s.get("status") != "ok"]
        total_collected = sum(s.get("count", 0) for s in report.source_stats)

        stat_rows = ""
        for s in sorted(report.source_stats, key=lambda x: -x.get("count", 0)):
            name = s.get("name", "")
            count = s.get("count", 0)
            status = s.get("status", "")
            access = s.get("access_method", "")
            if status == "ok":
                status_html = f'<span style="color:#27ae60">✓ {count} 条</span>'
            else:
                short_err = status[:40] + "..." if len(status) > 40 else status
                status_html = f'<span style="color:#c0392b" title="{_e(status)}">✗ {_e(short_err)}</span>'
            stat_rows += f"<tr><td>{_e(name)}</td><td style='color:#888;font-size:12px'>{_e(access)}</td><td>{status_html}</td></tr>"

        parts.append(f"""<h3 style="margin:24px 0 10px;font-size:15px">B. 本次采集统计
  <span style="font-weight:400;font-size:13px;color:#888;margin-left:8px">
    共抓取 {total_collected} 条 · {len(ok_stats)} 个信源成功 · {len(err_stats)} 个失败/超时
  </span>
</h3>
<table class="appendix-table">
  <tr><th>信源名称</th><th>接入方式</th><th>采集结果</th></tr>
  {stat_rows}
</table>""")

    return "\n".join(parts) if parts else '<p style="color:#888;font-size:14px">本期暂无来源记录。</p>'


def _render_x_feed(report: WeeklyReport) -> str:
    """渲染本周X平台热议栏目（Grok精选手动输入条目）。"""
    grok_items = [
        item for item in report.selected_items
        if item.source_name == "Grok精选"
    ]
    if not grok_items:
        return ""

    cards = []
    for item in grok_items:
        status = item.body_extraction_status or ""
        is_force = "force" in status
        # Extract author from status: "manual:force:@author" or "manual:@author"
        author = ""
        parts = status.split(":")
        for p in parts:
            if p.startswith("@"):
                author = p
                break

        force_badge = '<span class="x-force-badge">重点推荐</span>' if is_force else ""
        author_html = f'<span class="x-author">{_e(author)}</span>' if author else ""
        link_html = f'<a class="x-feed-link" href="{_e(item.url)}" target="_blank" rel="noopener">→ 原帖链接</a>' if item.url else ""
        card_class = "x-feed-card force-include" if is_force else "x-feed-card"

        # raw_text = summary + why_notable combined; split on first sentence boundary
        raw = item.raw_text or ""
        half = len(raw) // 2
        summary_part = raw[:half].strip() if half > 40 else raw
        why_part = raw[half:].strip() if half > 40 else ""

        cards.append(f"""<div class="{card_class}">
  <div class="x-feed-meta">{author_html}{force_badge}</div>
  <div class="x-feed-title">{_e(item.title)}</div>
  <div class="x-feed-why">{_e(summary_part)}</div>
  {f'<div class="x-feed-why" style="color:#777;font-size:12px">▸ {_e(why_part)}</div>' if why_part else ""}
  {link_html}
</div>""")

    inner = "\n".join(cards)
    count = len(grok_items)
    force_count = sum(1 for item in grok_items if "force" in (item.body_extraction_status or ""))
    subtitle = f'共 {count} 条 · {force_count} 条标记为重点推荐 · 来源：Grok精选'
    return f'<p style="font-size:13px;color:#888;margin-bottom:12px">{subtitle}</p>{inner}'


def _render_transcripts(report: WeeklyReport) -> str:
    """渲染本周精选博客/播客栏目（转录内容 + 手动指定博客）。"""
    _TRANSCRIPT_STATUSES = {"transcript_summarized", "web_transcript"}
    transcript_items = [
        item for item in report.selected_items
        if (
            item.body_extraction_status in _TRANSCRIPT_STATUSES
            or "手动指定" in (item.inclusion_reason or "")
            or item.source_type == "podcast"
        )
    ]
    if not transcript_items:
        return ""

    cards = []
    for item in transcript_items:
        date_str = _short_date(item.published_at)
        summary = item.summary or item.raw_text[:200]
        kp_html = ""
        if item.key_points:
            kp_items = "".join(f"<li>{_e(str(kp))}</li>" for kp in item.key_points[:5] if kp)
            kp_html = f'<ul style="padding-left:18px;margin:6px 0;font-size:13px;color:#444">{kp_items}</ul>'
        innovation = item.innovation or ""
        innovation_html = f'<p style="font-size:13px;color:#555;margin:6px 0"><strong>分析判断：</strong>{_e(innovation)}</p>' if innovation else ""
        link_html = f'<a href="{_e(item.url)}" target="_blank" rel="noopener" style="font-size:12px;color:#27ae60">→ 原始链接</a>' if item.url else ""
        badge_label = "精选博客" if item.body_extraction_status == "web_transcript" else "转录摘要"

        cards.append(f"""<div class="transcript-card">
  <div class="tc-meta">
    <span class="tc-badge">{badge_label}</span>
    <span>{_e(item.source_name)}</span>
    <span style="margin-left:8px;color:#aaa">{_e(date_str)}</span>
  </div>
  <div class="tc-title">{_e(item.title)}</div>
  <div class="tc-summary">{_e(summary)}</div>
  {kp_html}
  {innovation_html}
  {link_html}
</div>""")

    inner = "\n".join(cards)
    return f'<p style="font-size:13px;color:#888;margin-bottom:12px">共 {len(transcript_items)} 条精选博客/播客内容</p>{inner}'


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
