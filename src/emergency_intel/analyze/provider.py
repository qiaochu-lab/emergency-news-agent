from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List


class ProviderError(RuntimeError):
    pass


@dataclass
class ProviderClient:
    provider: str
    model: str
    api_base: str
    api_key: str
    timeout_seconds: int = 45

    def generate_structured_analysis(self, input_text: str, prompt_template: str) -> Dict[str, object]:
        if self.provider == "mock":
            return _mock_analysis(input_text)
        if self.provider == "openai_compatible":
            return self._call_openai_compatible(input_text, prompt_template)
        raise ProviderError(f"Unsupported provider: {self.provider}")

    def _call_openai_compatible(self, input_text: str, prompt_template: str) -> Dict[str, object]:
        if not self.api_key:
            raise ProviderError("EI_API_KEY is required for openai_compatible provider")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": input_text},
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            self.api_base,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"]
            return _normalize_analysis_payload(json.loads(content))
        except Exception as exc:
            raise ProviderError(str(exc)) from exc


def generate_structured_analysis(input_text: str, prompt_template: str, provider: ProviderClient) -> Dict[str, object]:
    return provider.generate_structured_analysis(input_text=input_text, prompt_template=prompt_template)


def _mock_analysis(input_text: str) -> Dict[str, object]:
    lines = [line.strip() for line in input_text.splitlines() if line.strip()]
    title = _field_after_prefix(lines, "标题: ") or "本条目"
    source = _field_after_prefix(lines, "来源: ") or "未知来源"
    domain = _field_after_prefix(lines, "领域: ") or "相关领域"
    body = _field_after_prefix(lines, "正文: ") or input_text
    body = body[:220]
    return {
        "summary": f"该事件来自{source}，核心涉及{domain}方向，反映出与“{title[:70]}”相关的能力、政策或应用进展正在推进。",
        "key_points": [
            "相关进展具备一定的行业应用或部署参考价值。",
            "建议结合后续公开披露与生态反馈判断其持续影响。"
        ],
        "innovation": f"值得关注之处在于其可能推动相关能力从概念验证走向更明确的应用或体系化布局。线索摘要：{body[:120]}",
        "takeaway": "短期内应重点观察其是否出现后续验证、规模化部署或政策层面的跟进动作。",
        "non_expert_explanation": "可以把它理解为一个值得持续追踪的行业信号，它可能影响后续技术投入、合作方向或应用节奏。",
    }


def _field_after_prefix(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def _normalize_analysis_payload(payload: Dict[str, Any]) -> Dict[str, object]:
    return {
        "summary": _to_text(payload.get("summary")),
        "key_points": _to_key_points(payload.get("key_points")),
        "innovation": _to_text(payload.get("innovation")),
        "takeaway": _to_text(payload.get("takeaway")),
        "non_expert_explanation": _to_text(payload.get("non_expert_explanation")),
        "content_type": _to_text(payload.get("content_type")),
        "why_this_week": _to_text(payload.get("why_this_week")),
        "inclusion_reason": _to_text(payload.get("inclusion_reason")),
        "analyst_note": _to_text(payload.get("analyst_note")),
        "week_relevance": _to_text(payload.get("week_relevance")),
        "is_this_week_signal": _to_bool(payload.get("is_this_week_signal")),
        "include_in_top_report": _to_bool(payload.get("include_in_top_report")),
        "emergency_relevance_score": _to_int(payload.get("emergency_relevance_score")),
        "communication_relevance_score": _to_int(payload.get("communication_relevance_score")),
    }


def _to_key_points(value: Any) -> List[str]:
    if isinstance(value, list):
        points: List[str] = []
        for item in value:
            text = _to_text(item)
            if text:
                points.append(text)
        return points
    text = _to_text(value)
    return [text] if text else []


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split()).strip()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        parts = [_to_text(item) for item in value]
        return "；".join(part for part in parts if part)
    if isinstance(value, dict):
        parts = []
        for key, nested in value.items():
            nested_text = _to_text(nested)
            if nested_text:
                parts.append(f"{key}: {nested_text}")
        return "；".join(parts)
    return str(value).strip()


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "yes"}:
            return True
        if lowered in {"false", "no"}:
            return False
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None
