import json, os, dataclasses
from dotenv import load_dotenv
load_dotenv(dotenv_path='.env')

from emergency_intel.analyze.service import analyze_items
from emergency_intel.report.service import build_weekly_report
from emergency_intel.report.html_renderer import render_report_html
from emergency_intel.analyze.provider import ProviderClient
from emergency_intel.config import Settings, DATA_DIR, OUTPUTS_DIR
from emergency_intel.models import ScoredItem

settings = Settings()

data = json.loads(open('data/enriched/items.json').read())
target_ids = [
    'tavily-https-www-cisa-gov-safecom-field-operations-guides',
    'tavily-https-www-police1-com-911-and-dispatch-smarter-faster-safer-how-ai-is-reinvent',
]
raw_items = [d for d in data if d.get('id') in target_ids]
print(f"找到 {len(raw_items)} 条原始数据")

valid_keys = {f.name for f in dataclasses.fields(ScoredItem)}

scored_items = []
for d in raw_items:
    filtered = {k: v for k, v in d.items() if k in valid_keys}
    filtered.update({
        'include_in_top_report': True,
        'is_this_week_signal': True,
        'final_score': max(float(d.get('final_score', 7.0)), 7.0),
        'importance_score': float(d.get('importance_score', 5.0)),
        'heat_score': float(d.get('heat_score', 3.0)),
        'content_type': 'article',
        'report_content_type': 'article',
        'week_relevance': 'high',
        'emergency_relevance_score': 8.0,
        'communication_relevance_score': 8.0,
        'inclusion_reason': '',
        'analyst_note': '',
        'why_this_week': '',
    })
    for f in dataclasses.fields(ScoredItem):
        if f.name not in filtered:
            filtered[f.name] = f.default if f.default is not dataclasses.MISSING else (
                f.default_factory() if f.default_factory is not dataclasses.MISSING else None
            )
    scored_items.append(ScoredItem(**filtered))

print(f"构建 ScoredItem: {len(scored_items)} 条")
for item in scored_items:
    print(f"  {item.title[:70]} | include={item.include_in_top_report} | score={item.final_score}")

provider = ProviderClient(
    provider=settings.provider, model=settings.model,
    api_base=settings.api_base, api_key=settings.api_key,
    timeout_seconds=settings.llm_timeout_seconds,
)

analyzed_path = DATA_DIR / 'scored' / 'test_analyzed.json'
analyzed = analyze_items(scored_items, analyzed_path, provider, minimum_score=0.0)
print(f"分析完成: {len(analyzed)} 条")
for a in analyzed:
    print(f"  {a.title[:70]} | summary={len(a.summary)}字 | glossary={len(a.glossary_terms)}条")

report = build_weekly_report(analyzed, '2026-W14', source_stats=[])
print(f"报告条数: {len(report.selected_items)}")

out = OUTPUTS_DIR / 'weekly' / '测试输出_两条_test.html'
render_report_html(report, out)
print('生成完成:', out)
