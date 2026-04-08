"""
Generate an interactive HTML review page alongside the weekly review.md.

The page lets users click [ok]/[wrong] and [skip]/[should] buttons per item,
then exports the annotated content as a review.md-compatible text block
for copy-pasting (or direct save) into data/feedback/YYYY-WXX-review.md.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from emergency_intel.models import ScoredItem


def render_review_html(
    included: List[ScoredItem],
    excluded: List[ScoredItem],
    week_label: str,
    out_path: Path,
) -> Path:
    """Write the interactive review HTML to *out_path* and return the path."""
    html = _build_html(included, excluded, week_label)
    out_path.write_text(html, encoding="utf-8")
    return out_path


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _item_row(item: ScoredItem, default_mark: str, alt_mark: str, color: str) -> str:
    domain = ", ".join(item.domain_tags) if item.domain_tags else item.source_type
    safe_title = item.title.replace('"', "&quot;").replace("'", "&#39;")
    safe_domain = domain.replace('"', "&quot;")
    safe_source = item.source_name.replace('"', "&quot;")
    url = item.url or "#"

    return f"""
    <div class="item" id="item-{item.id}"
         data-score="{item.final_score:.1f}"
         data-title="{safe_title}"
         data-domain="{safe_domain}"
         data-source="{safe_source}"
         data-mark="{default_mark}">
      <div class="item-meta">
        <span class="score">{item.final_score:.1f}</span>
        <span class="domain">{domain}</span>
        <span class="source">{item.source_name}</span>
      </div>
      <div class="item-title">
        <a href="{url}" target="_blank" rel="noopener">{item.title}</a>
      </div>
      <div class="item-actions">
        <button class="btn btn-default active" onclick="setMark('{item.id}', '{default_mark}', this)">[{default_mark}]</button>
        <button class="btn btn-alt" style="background:{color}" onclick="setMark('{item.id}', '{alt_mark}', this)">[{alt_mark}]</button>
      </div>
    </div>"""


def _build_html(included: List[ScoredItem], excluded: List[ScoredItem], week_label: str) -> str:
    included_rows = "\n".join(
        _item_row(item, "ok", "wrong", "#e74c3c") for item in included
    )
    excluded_rows = "\n".join(
        _item_row(item, "skip", "should", "#27ae60") for item in excluded
    )

    included_count = len(included)
    excluded_count = len(excluded)

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>周报反馈审阅 — {week_label}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; background: #f5f6fa; color: #2c3e50; }}
  header {{ background: #2c3e50; color: #fff; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; }}
  header h1 {{ font-size: 1.2rem; font-weight: 600; }}
  header .week {{ font-size: 0.9rem; opacity: 0.7; }}
  .container {{ max-width: 900px; margin: 32px auto; padding: 0 16px; }}
  .section-title {{ font-size: 1rem; font-weight: 700; margin: 28px 0 12px;
                    padding: 8px 14px; border-radius: 6px; }}
  .section-included {{ background: #eaf4fb; color: #1a6fa0; }}
  .section-excluded {{ background: #eafaf1; color: #1a7a45; }}
  .item {{ background: #fff; border-radius: 8px; padding: 14px 16px;
           margin-bottom: 8px; border: 1px solid #e0e0e0;
           transition: border-color .15s; }}
  .item[data-mark="wrong"] {{ border-left: 4px solid #e74c3c; }}
  .item[data-mark="should"] {{ border-left: 4px solid #27ae60; }}
  .item[data-mark="ok"] {{ border-left: 4px solid #bdc3c7; }}
  .item[data-mark="skip"] {{ border-left: 4px solid #bdc3c7; opacity: .75; }}
  .item-meta {{ font-size: 0.78rem; color: #7f8c8d; margin-bottom: 5px; display: flex; gap: 12px; }}
  .score {{ font-weight: 700; color: #e67e22; }}
  .item-title a {{ font-size: 0.95rem; font-weight: 500; color: #2c3e50;
                   text-decoration: none; }}
  .item-title a:hover {{ text-decoration: underline; }}
  .item-actions {{ margin-top: 10px; display: flex; gap: 8px; }}
  .btn {{ border: none; border-radius: 4px; padding: 5px 14px; font-size: 0.8rem;
          cursor: pointer; font-family: monospace; background: #ecf0f1; color: #555;
          transition: background .15s, color .15s; }}
  .btn.active {{ background: #2c3e50; color: #fff; }}
  .export-bar {{ position: sticky; top: 0; z-index: 100; background: #fff;
                 border-bottom: 1px solid #ddd; padding: 12px 32px;
                 display: flex; gap: 12px; align-items: center; }}
  .export-bar button {{ background: #2980b9; color: #fff; border: none;
                        border-radius: 6px; padding: 8px 20px; font-size: 0.9rem;
                        cursor: pointer; }}
  .export-bar button:hover {{ background: #1a6fa0; }}
  .export-bar .hint {{ font-size: 0.8rem; color: #888; }}
  #export-modal {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,.5);
                   z-index: 200; align-items: center; justify-content: center; }}
  #export-modal.open {{ display: flex; }}
  .modal-box {{ background: #fff; border-radius: 10px; padding: 24px;
                max-width: 680px; width: 90%; max-height: 80vh; display: flex;
                flex-direction: column; gap: 12px; }}
  .modal-box h2 {{ font-size: 1rem; }}
  .modal-box textarea {{ flex: 1; min-height: 320px; font-family: monospace;
                          font-size: 0.82rem; border: 1px solid #ddd; border-radius: 6px;
                          padding: 10px; resize: vertical; }}
  .modal-actions {{ display: flex; gap: 10px; }}
  .modal-actions button {{ border: none; border-radius: 6px; padding: 8px 18px;
                            cursor: pointer; font-size: 0.85rem; }}
  .btn-copy {{ background: #27ae60; color: #fff; }}
  .btn-close {{ background: #ecf0f1; color: #555; }}
  .note {{ font-size: 0.8rem; color: #888; background: #fafafa;
           border: 1px solid #eee; border-radius: 6px; padding: 10px 14px;
           margin-bottom: 16px; }}
</style>
</head>
<body>

<header>
  <h1>周报反馈审阅</h1>
  <span class="week">{week_label}</span>
</header>

<div class="export-bar">
  <button onclick="openExport()">导出 review.md</button>
  <span class="hint">标注完成后点击导出，将内容覆盖保存到 data/feedback/{week_label}-review.md</span>
</div>

<div class="container">

  <p class="note">
    <strong>使用方式：</strong>
    点击每条右侧按钮切换标注。<br>
    已入报条目：默认 <code>[ok]</code>，点 <code>[wrong]</code> 表示「不该入选」<br>
    被排除条目：默认 <code>[skip]</code>，点 <code>[should]</code> 表示「应该入选」<br>
    标注完成后点击上方「导出 review.md」，复制内容保存到对应文件。
  </p>

  <div class="section-title section-included">已入报（{included_count} 条）</div>
  {included_rows if included_rows else '<p style="color:#888;padding:8px">本期无入报条目</p>'}

  <div class="section-title section-excluded">被排除但本周相关（评分 ≥ 4.0，共 {excluded_count} 条）</div>
  {excluded_rows if excluded_rows else '<p style="color:#888;padding:8px">无符合条件的排除条目</p>'}

</div>

<div id="export-modal">
  <div class="modal-box">
    <h2>导出 review.md 内容</h2>
    <textarea id="export-content" readonly></textarea>
    <p style="font-size:0.8rem;color:#888">复制上方内容，覆盖保存到：<code>data/feedback/{week_label}-review.md</code></p>
    <div class="modal-actions">
      <button class="btn-copy" onclick="copyExport()">复制到剪贴板</button>
      <button class="btn-close" onclick="closeExport()">关闭</button>
    </div>
  </div>
</div>

<script>
function setMark(id, mark, btn) {{
  var item = document.getElementById('item-' + id);
  item.dataset.mark = mark;
  var btns = item.querySelectorAll('.btn');
  btns.forEach(function(b) {{ b.classList.remove('active'); }});
  btn.classList.add('active');
}}

function buildMarkdown() {{
  var lines = ['# 周报反馈审阅 — {week_label}', ''];

  // included section
  var includedItems = document.querySelectorAll('.item');
  var included = [], excluded = [];
  includedItems.forEach(function(el) {{
    var mark = el.dataset.mark;
    if (mark === 'ok' || mark === 'wrong') included.push(el);
    else excluded.push(el);
  }});

  lines.push('## 已入报（' + included.length + ' 条）', '');
  included.forEach(function(el) {{
    lines.push('- [' + el.dataset.mark + '] ' + el.dataset.score + ' | ' +
      el.dataset.title + ' | ' + el.dataset.domain + ' | ' + el.dataset.source);
  }});

  lines.push('', '## 被排除但本周相关（评分 ≥ 4.0，共 ' + excluded.length + ' 条）', '');
  excluded.forEach(function(el) {{
    lines.push('- [' + el.dataset.mark + '] ' + el.dataset.score + ' | ' +
      el.dataset.title + ' | ' + el.dataset.domain + ' | ' + el.dataset.source);
  }});

  lines.push('', '---', '', '## 补充意见', '', '（在此写本期整体反馈）', '', '');
  return lines.join('\\n');
}}

function openExport() {{
  document.getElementById('export-content').value = buildMarkdown();
  document.getElementById('export-modal').classList.add('open');
}}

function closeExport() {{
  document.getElementById('export-modal').classList.remove('open');
}}

function copyExport() {{
  var ta = document.getElementById('export-content');
  ta.select();
  document.execCommand('copy');
  var btn = document.querySelector('.btn-copy');
  btn.textContent = '已复制！';
  setTimeout(function() {{ btn.textContent = '复制到剪贴板'; }}, 1500);
}}

document.getElementById('export-modal').addEventListener('click', function(e) {{
  if (e.target === this) closeExport();
}});
</script>
</body>
</html>"""
