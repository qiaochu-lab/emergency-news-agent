from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class RawItem:
    id: str
    source_type: str
    source_name: str
    title: str
    url: str
    published_at: str
    language: str
    raw_text: str
    content_depth: str = "summary"
    body_extraction_status: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedItem(RawItem):
    domain_tags: List[str] = field(default_factory=list)
    entity_tags: List[str] = field(default_factory=list)
    region_tags: List[str] = field(default_factory=list)
    content_type: str = "news"
    evidence_level: str = "Secondary mention"
    normalized_title: str = ""
    canonical_url: str = ""
    content_fingerprint: str = ""


@dataclass
class ScoredItem(NormalizedItem):
    importance_score: float = 0.0
    heat_score: float = 0.0
    final_score: float = 0.0
    report_content_type: str = ""
    is_this_week_signal: bool = False
    why_this_week: str = ""
    emergency_relevance_score: int = 0
    communication_relevance_score: int = 0
    include_in_top_report: bool = False
    inclusion_reason: str = ""
    analyst_note: str = ""
    week_relevance: str = ""
    thumbnail_url: str = ""


@dataclass
class AnalyzedItem(ScoredItem):
    summary: str = ""
    key_points: List[str] = field(default_factory=list)
    innovation: str = ""
    takeaway: str = ""
    non_expert_explanation: str = ""


@dataclass
class WeeklyReport:
    week_range: str
    selected_items: List[AnalyzedItem]
    section_summaries: Dict[str, str]
    weekly_insights: List[str]
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["selected_items"] = [asdict(item) for item in self.selected_items]
        return data
