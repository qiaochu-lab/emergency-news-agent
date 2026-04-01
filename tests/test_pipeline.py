from __future__ import annotations

import sys
import tempfile
import time
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from emergency_intel.analyze.provider import ProviderClient, ProviderError, _normalize_analysis_payload, generate_structured_analysis
from emergency_intel.analyze.service import _prompt_for_item, screen_items
from emergency_intel.audit import audit_raw_item
from emergency_intel.collect.adapters import SourceAdapter, _discover_article_links
from emergency_intel.collect.service import collect_items
from emergency_intel.classify.service import classify_items
from emergency_intel.dedup.service import deduplicate_items
from emergency_intel.enrich.service import enrich_fulltext
from emergency_intel.models import NormalizedItem, RawItem, ScoredItem
from emergency_intel.pipeline import _report_filename, run_weekly_pipeline
from emergency_intel.scheduler import next_run_time


class PipelineTests(unittest.TestCase):
    def test_dedup_removes_same_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            items = [
                NormalizedItem(
                    id="1",
                    source_type="news",
                    source_name="A",
                    title="Same",
                    url="https://example.com/a?x=1",
                    published_at="2026-03-20",
                    language="en",
                    raw_text="alpha",
                    normalized_title="same",
                    canonical_url="https://example.com/a",
                    content_fingerprint="fp-1",
                ),
                NormalizedItem(
                    id="2",
                    source_type="news",
                    source_name="B",
                    title="Same but copied",
                    url="https://example.com/a?x=2",
                    published_at="2026-03-20",
                    language="en",
                    raw_text="beta",
                    normalized_title="same but copied",
                    canonical_url="https://example.com/a",
                    content_fingerprint="fp-2",
                ),
            ]
            deduped, removed = deduplicate_items(items, Path(tmpdir) / "deduped.json")
        self.assertEqual(1, len(deduped))
        self.assertEqual(1, removed)

    def test_classifier_assigns_expected_domain(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            item = NormalizedItem(
                id="1",
                source_type="official",
                source_name="Agency",
                title="Drone pilot improves search and rescue",
                url="https://example.com/drone",
                published_at="2026-03-20",
                language="en",
                raw_text="The emergency response agency announced a UAV deployment.",
                normalized_title="drone pilot improves search and rescue",
                canonical_url="https://example.com/drone",
                content_fingerprint="fp",
            )
            classified = classify_items([item], Path(tmpdir) / "classified.json")
        self.assertIn("Drones", classified[0].domain_tags)
        self.assertIn("Emergency Response", classified[0].domain_tags)

    def test_mock_provider_returns_structure(self) -> None:
        provider = ProviderClient(provider="mock", model="mock", api_base="", api_key="")
        result = generate_structured_analysis("标题: test", "prompt", provider)
        self.assertIn("summary", result)
        self.assertIn("key_points", result)
        self.assertNotIn("标题:", result["summary"])

    def test_openai_compatible_provider_wraps_transport_errors(self) -> None:
        provider = ProviderClient(provider="openai_compatible", model="m", api_base="https://example.com", api_key="k", timeout_seconds=1)
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(ProviderError, "timed out"):
                provider.generate_structured_analysis("test", "prompt")

    def test_analysis_payload_normalization_flattens_nested_values(self) -> None:
        payload = {
            "summary": "summary",
            "key_points": [
                {"fact": "f1", "judgment": "j1"},
                "plain point",
            ],
            "innovation": {"technical_focus": "mesh", "impact": "high"},
            "takeaway": {"short_term": "watch", "signals": ["policy", "deploy"]},
            "non_expert_explanation": {"core": "simple"},
        }
        normalized = _normalize_analysis_payload(payload)
        self.assertEqual("summary", normalized["summary"])
        self.assertEqual(["fact: f1；judgment: j1", "plain point"], normalized["key_points"])
        self.assertIn("technical_focus: mesh", normalized["innovation"])
        self.assertIn("short_term: watch", normalized["takeaway"])

    def test_article_link_discovery_filters_article_urls(self) -> None:
        html = """
        <html><body>
        <a href="/2026/03/incident-response-upgrade">article</a>
        <a href="/about">about</a>
        <a href="https://example.com/news/new-satellite-link">news</a>
        </body></html>
        """
        links = _discover_article_links("https://example.com", html)
        self.assertEqual(
            [
                "https://example.com/2026/03/incident-response-upgrade",
                "https://example.com/news/new-satellite-link",
            ],
            links,
        )

    def test_raw_item_audit_labels_short_summary(self) -> None:
        item = RawItem(
            id="1",
            source_type="news",
            source_name="A",
            title="Short summary",
            url="https://example.com/article",
            published_at="2026-03-20",
            language="en",
            raw_text="This is a short summary about an emergency drone deployment.",
        )
        audited = audit_raw_item(item)
        self.assertEqual("short_summary", audited["quality_label"])

    def test_x_api_adapter_maps_recent_search_results(self) -> None:
        adapter = SourceAdapter(
            source={
                "name": "X - Jack Clark",
                "source_type": "forum",
                "access_method": "api",
                "api_provider": "x",
                "username": "jackclarkSF",
                "query": "from:jackclarkSF -is:retweet",
                "language": "en",
            }
        )
        payload = {
            "data": [
                {
                    "id": "1900000000000000001",
                    "text": "A useful note on frontier models for emergency coordination.",
                    "created_at": "2026-03-24T12:34:56.000Z",
                    "lang": "en",
                }
            ]
        }
        with patch.dict("os.environ", {"EI_X_BEARER_TOKEN": "test-token"}, clear=False):
            with patch("emergency_intel.collect.adapters._download_json", return_value=payload) as mock_download:
                items = adapter.fetch()

        self.assertEqual(1, len(items))
        self.assertEqual("X - Jack Clark", items[0].source_name)
        self.assertEqual("https://x.com/jackclarkSF/status/1900000000000000001", items[0].url)
        self.assertIn("frontier models", items[0].raw_text)
        request_url = mock_download.call_args.args[0]
        self.assertIn("api.x.com/2/tweets/search/recent", request_url)
        self.assertIn("from%3AjackclarkSF%20-is%3Aretweet", request_url)

    def test_x_api_adapter_requires_bearer_token(self) -> None:
        adapter = SourceAdapter(
            source={
                "name": "X - Jack Clark",
                "source_type": "forum",
                "access_method": "api",
                "api_provider": "x",
                "username": "jackclarkSF",
            }
        )
        with patch.dict("os.environ", {"EI_X_BEARER_TOKEN": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "EI_X_BEARER_TOKEN"):
                adapter.fetch()

    def test_scheduler_computes_future_run(self) -> None:
        current = datetime(2026, 3, 25, 10, 30)
        nxt = next_run_time(current, "MON", 9)
        self.assertGreater(nxt, current)
        self.assertEqual(0, nxt.weekday())
        self.assertEqual(9, nxt.hour)

    def test_prompt_selection_varies_by_source_type(self) -> None:
        official = ScoredItem(id="1", source_type="official", source_name="NIST", title="Official", url="u", published_at="2026-03-20", language="en", raw_text="t")
        paper = ScoredItem(id="2", source_type="paper", source_name="arXiv", title="Paper", url="u", published_at="2026-03-20", language="en", raw_text="t")
        forum = ScoredItem(id="3", source_type="forum", source_name="X", title="Forum", url="u", published_at="2026-03-20", language="en", raw_text="t")
        news = ScoredItem(id="4", source_type="news", source_name="News", title="News", url="u", published_at="2026-03-20", language="en", raw_text="t")

        self.assertIn("official announcement", _prompt_for_item(official).lower())
        self.assertIn("research paper", _prompt_for_item(paper).lower())
        self.assertIn("community or social signal", _prompt_for_item(forum).lower())
        self.assertIn("news item", _prompt_for_item(news).lower())

    def test_parse_date_supports_rfc2822(self) -> None:
        from emergency_intel.analyze.service import _parse_date
        self.assertEqual(date(2026, 3, 28), _parse_date("Fri, 28 Mar 2026 12:00:00 GMT"))

    def test_screening_excludes_resource_pages_and_old_background_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            items = [
                ScoredItem(
                    id="1",
                    source_type="official",
                    source_name="DARPA",
                    title="Small Business | DARPA",
                    url="https://www.darpa.mil/work-with-us/communities/small-business",
                    published_at="2026-03-20T10:00:00Z",
                    language="en",
                    raw_text="Small businesses drive the economy and exemplify the innovative spirit.",
                    domain_tags=["AI", "Communications"],
                    final_score=7.8,
                ),
                ScoredItem(
                    id="2",
                    source_type="paper",
                    source_name="arXiv",
                    title="Resilient Mesh Communications for Disaster Zones",
                    url="https://arxiv.org/abs/2603.00001",
                    published_at="2026-03-21T10:00:00Z",
                    language="en",
                    raw_text="A new paper on resilient mesh communications for emergency response.",
                    domain_tags=["Communications", "Emergency Response"],
                    final_score=8.2,
                ),
                ScoredItem(
                    id="3",
                    source_type="paper",
                    source_name="arXiv",
                    title="Old but related paper",
                    url="https://arxiv.org/abs/2407.00001",
                    published_at="2024-07-10T10:00:00Z",
                    language="en",
                    raw_text="A related but old background paper about emergency networks.",
                    domain_tags=["Communications", "Emergency Response"],
                    final_score=8.9,
                ),
            ]
            screened = screen_items(
                items,
                Path(tmpdir) / "screened.json",
                ProviderClient(provider="mock", model="mock", api_base="", api_key=""),
                reference_date=date(2026, 3, 25),
            )
        self.assertFalse(screened[0].include_in_top_report)
        self.assertEqual("resource", screened[0].report_content_type)
        self.assertTrue(screened[1].include_in_top_report)
        self.assertFalse(screened[2].include_in_top_report)
        self.assertIn("不在本周区间", screened[2].why_this_week)

    def test_screening_includes_strategic_company_update_in_week(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            items = [
                ScoredItem(
                    id="company-1",
                    source_type="company",
                    source_name="OpenAI News RSS",
                    title="How we monitor internal coding agents for misalignment",
                    url="https://openai.com/news/internal-coding-agents",
                    published_at="Thu, 19 Mar 2026 10:00:00 GMT",
                    language="en",
                    raw_text="OpenAI describes how model monitoring and agent safety work in production systems.",
                    domain_tags=["AI"],
                    final_score=3.75,
                )
            ]
            screened = screen_items(
                items,
                Path(tmpdir) / "screened.json",
                ProviderClient(provider="mock", model="mock", api_base="", api_key=""),
                reference_date=date(2026, 3, 25),
            )
        self.assertTrue(screened[0].include_in_top_report)
        self.assertEqual("company_update", screened[0].report_content_type)

    def test_report_filename_uses_mode_or_registry_stem(self) -> None:
        registry_path = Path("/tmp/live_quick.json")
        real_name = _report_filename("2026-03-16 to 2026-03-22", registry_path, use_mock_data=False)
        mock_name = _report_filename("2026-03-16 to 2026-03-22", registry_path, use_mock_data=True)
        self.assertEqual("2026-03-16_2026-03-22_live_quick_industry_brief.md", real_name)
        self.assertEqual("2026-03-16_2026-03-22_mock_industry_brief.md", mock_name)

    def test_enrich_fulltext_upgrades_high_signal_web_item(self) -> None:
        item = ScoredItem(
            id="1",
            source_type="official",
            source_name="Agency",
            title="New policy",
            url="https://example.com/policy",
            published_at="2026-03-21T10:00:00Z",
            language="en",
            raw_text="Short summary only.",
            final_score=8.0,
            include_in_top_report=True,
            report_content_type="official_announcement",
        )
        html = "<html><body><article>" + ("Policy body " * 200) + "</article></body></html>"
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("emergency_intel.enrich.service._download_response_text", return_value=html):
                enriched = enrich_fulltext([item], Path(tmpdir) / "enriched.json", timeout_seconds=2)
        self.assertEqual("enriched", enriched[0].body_extraction_status)
        self.assertEqual("fulltext", enriched[0].content_depth)
        self.assertGreater(len(enriched[0].raw_text), len(item.raw_text))

    def test_collect_items_records_timeout_per_source(self) -> None:
        registry = [
            {"name": "Slow Source", "source_type": "news", "access_method": "web", "url": "https://example.com"},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "registry.json"
            registry_path.write_text(__import__("json").dumps(registry), encoding="utf-8")
            with patch("emergency_intel.collect.service.build_adapters") as mock_build:
                adapter = type("Adapter", (), {"source": {"name": "Slow Source"}, "fetch": lambda self: time.sleep(0.2) or []})()
                mock_build.return_value = [adapter]
                items, errors = collect_items(registry_path, Path(tmpdir) / "raw.json", per_source_timeout_seconds=0)
        self.assertEqual([], items)
        self.assertEqual(1, len(errors))
        self.assertIn("timeout", errors[0])

    def test_pipeline_generates_markdown_with_mock_data(self) -> None:
        result = run_weekly_pipeline(reference_date=date(2026, 3, 25), use_mock_data=True)
        self.assertGreaterEqual(result["items_selected"], 1)
        self.assertGreaterEqual(result["items_screened_in"], 1)
        report_path = Path(result["report_path"])
        self.assertTrue(report_path.exists())
        content = report_path.read_text(encoding="utf-8")
        self.assertIn("# 泛应急技术行业周报", content)
        self.assertIn("# 报告要点", content)
        self.assertIn("# 1 周度景气与板块变化", content)
        self.assertIn("# 2 本周重点新闻与分析", content)
        self.assertIn("# 3 本周及下周重点公告 / 事件日历", content)
        self.assertIn("# 4 建议关注方向", content)
        self.assertIn("# 5 风险提示", content)
        self.assertTrue((ROOT / "docs" / "weekly_run_log.md").exists())


if __name__ == "__main__":
    unittest.main()
