from __future__ import annotations

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Dict, Iterable, List
from urllib.parse import quote, urljoin, urlparse

from emergency_intel.models import RawItem
from emergency_intel.utils import normalize_whitespace, slugify, utc_now_iso


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())


class _HTMLLinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


@dataclass
class SourceAdapter:
    source: Dict[str, object]

    def fetch(self) -> List[RawItem]:
        access_method = str(self.source.get("access_method", "web"))
        if access_method == "rss":
            return self._fetch_rss()
        if access_method == "api":
            return self._fetch_api()
        if access_method == "github_json_feed":
            return self._fetch_github_json_feed()
        return self._fetch_web()

    def _fetch_rss(self) -> List[RawItem]:
        content = _download_text(str(self.source["url"]))
        root = ET.fromstring(content)
        items: List[RawItem] = []
        max_items = int(self.source.get("max_items", 20))

        # Try RSS <item> first, then Atom <entry>
        rss_nodes = root.findall(".//item")
        if rss_nodes:
            for node in rss_nodes[:max_items]:
                title = node.findtext("title", default="Untitled")
                link = node.findtext("link", default=str(self.source["url"]))
                description = node.findtext("description", default="")
                pub_date = node.findtext("pubDate", default=utc_now_iso())
                items.append(
                    RawItem(
                        id=f"{slugify(str(self.source['name']))}-{slugify(title)[:40]}",
                        source_type=str(self.source["source_type"]),
                        source_name=str(self.source["name"]),
                        title=normalize_whitespace(title),
                        url=link.strip(),
                        published_at=pub_date,
                        language=str(self.source.get("language", "en")),
                        raw_text=normalize_whitespace(description or title),
                        content_depth="summary",
                        body_extraction_status="rss_summary",
                    )
                )
        else:
            # Atom feed fallback
            atom_ns = "http://www.w3.org/2005/Atom"
            ns = {"atom": atom_ns}
            for entry in root.findall("atom:entry", ns)[:max_items]:
                title = entry.findtext("atom:title", default="Untitled", namespaces=ns)
                link_el = entry.find("atom:link[@rel='alternate']", ns) or entry.find("atom:link", ns)
                link = link_el.get("href", str(self.source["url"])) if link_el is not None else str(self.source["url"])
                summary = entry.findtext("atom:summary", default="", namespaces=ns) or entry.findtext("atom:content", default="", namespaces=ns)
                pub_date = entry.findtext("atom:published", default=utc_now_iso(), namespaces=ns) or entry.findtext("atom:updated", default=utc_now_iso(), namespaces=ns)
                items.append(
                    RawItem(
                        id=f"{slugify(str(self.source['name']))}-{slugify(title)[:40]}",
                        source_type=str(self.source["source_type"]),
                        source_name=str(self.source["name"]),
                        title=normalize_whitespace(title),
                        url=link.strip(),
                        published_at=pub_date,
                        language=str(self.source.get("language", "en")),
                        raw_text=normalize_whitespace(summary or title),
                        content_depth="summary",
                        body_extraction_status="rss_summary",
                    )
                )

        items.sort(key=lambda item: _sort_key_for_published_at(item.published_at), reverse=True)
        return items

    def _fetch_github_json_feed(self) -> List[RawItem]:
        """Fetch pre-compiled JSON feeds from public GitHub repos (e.g. follow-builders)."""
        payload = _download_json(str(self.source["url"]))
        source_name = str(self.source["name"])
        source_type = str(self.source["source_type"])
        language = str(self.source.get("language", "en"))
        max_items = int(self.source.get("max_items", 20))

        # feed-x.json: {"x": [{"handle":..., "tweets": [...]}]}
        if "x" in payload:
            return self._parse_github_x_feed(payload, source_name, source_type, language, max_items)

        # feed-blogs.json: {"blogs": [{"source":..., "title":..., "url":..., "publishedAt":..., "excerpt":...}]}
        if "blogs" in payload:
            return self._parse_github_blogs_feed(payload, source_name, source_type, language, max_items)

        return []

    def _parse_github_x_feed(
        self, payload: dict, source_name: str, source_type: str, language: str, max_items: int
    ) -> List[RawItem]:
        items: List[RawItem] = []
        count = 0
        for account in payload.get("x", []):
            handle = str(account.get("handle", "unknown"))
            for tweet in account.get("tweets", []):
                if count >= max_items:
                    break
                post_id = str(tweet.get("id", "")).strip()
                text = normalize_whitespace(str(tweet.get("text", "")).replace("\n", " "))
                if not post_id or not text:
                    continue
                url = str(tweet.get("url", f"https://x.com/{handle}/status/{post_id}"))
                created_at = str(tweet.get("createdAt", utc_now_iso()))
                items.append(
                    RawItem(
                        id=f"{slugify(source_name)}-{post_id}",
                        source_type=source_type,
                        source_name=source_name,
                        title=text[:120],
                        url=url,
                        published_at=created_at,
                        language=language,
                        raw_text=text[:6000],
                        content_depth="headline",
                        body_extraction_status="x_post",
                    )
                )
                count += 1
            if count >= max_items:
                break
        return items

    def _parse_github_blogs_feed(
        self, payload: dict, source_name: str, source_type: str, language: str, max_items: int
    ) -> List[RawItem]:
        items: List[RawItem] = []
        for entry in payload.get("blogs", [])[:max_items]:
            title = normalize_whitespace(str(entry.get("title", "Untitled")))
            url = str(entry.get("url", ""))
            published_at = str(entry.get("publishedAt", utc_now_iso()))
            excerpt = normalize_whitespace(str(entry.get("excerpt", "")))
            blog_source = str(entry.get("source", source_name))
            if not title or not url:
                continue
            items.append(
                RawItem(
                    id=f"{slugify(source_name)}-{slugify(title)[:50]}",
                    source_type=source_type,
                    source_name=blog_source,
                    title=title,
                    url=url,
                    published_at=published_at,
                    language=language,
                    raw_text=(excerpt or title)[:6000],
                    content_depth="summary" if excerpt else "headline",
                    body_extraction_status="github_blog_feed",
                )
            )
        return items

    def _fetch_api(self) -> List[RawItem]:
        if str(self.source.get("api_provider", "")).lower() == "x":
            return self._fetch_x_api()

        content = _download_text(str(self.source["url"]))
        if "arxiv" in str(self.source["url"]):
            root = ET.fromstring(content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            items: List[RawItem] = []
            for entry in root.findall("atom:entry", ns):
                title = entry.findtext("atom:title", default="Untitled", namespaces=ns)
                link = entry.find("atom:id", ns)
                summary = entry.findtext("atom:summary", default="", namespaces=ns)
                published = entry.findtext("atom:published", default=utc_now_iso(), namespaces=ns)
                items.append(
                    RawItem(
                        id=f"{slugify(str(self.source['name']))}-{slugify(title)[:40]}",
                        source_type=str(self.source["source_type"]),
                        source_name=str(self.source["name"]),
                        title=normalize_whitespace(title),
                        url=link.text if link is not None else str(self.source["url"]),
                        published_at=published,
                        language=str(self.source.get("language", "en")),
                        raw_text=normalize_whitespace(summary or title),
                        content_depth="summary",
                        body_extraction_status="api_summary",
                    )
                )
            return items

        payload = json.loads(content)
        items = []
        for entry in payload.get("items", []):
            title = str(entry.get("title", "Untitled"))
            items.append(
                RawItem(
                    id=f"{slugify(str(self.source['name']))}-{slugify(title)[:40]}",
                    source_type=str(self.source["source_type"]),
                    source_name=str(self.source["name"]),
                    title=normalize_whitespace(title),
                    url=str(entry.get("url", self.source["url"])),
                    published_at=str(entry.get("published_at", utc_now_iso())),
                    language=str(entry.get("language", self.source.get("language", "en"))),
                    raw_text=normalize_whitespace(str(entry.get("raw_text", title))),
                    content_depth="summary",
                    body_extraction_status="api_payload",
                )
            )
        return items

    def _fetch_x_api(self) -> List[RawItem]:
        bearer_token = os.getenv("EI_X_BEARER_TOKEN", "").strip()
        if not bearer_token:
            raise ValueError("EI_X_BEARER_TOKEN is required for X API sources")

        username = str(self.source.get("username", "")).strip().lstrip("@")
        query = str(self.source.get("query", "")).strip()
        if not query and username:
            query = f"from:{username} -is:retweet"
        if not query:
            raise ValueError("X API source requires either 'username' or 'query'")

        max_results = int(self.source.get("max_results", 10))
        max_results = max(10, min(max_results, 100))
        endpoint = (
            "https://api.x.com/2/tweets/search/recent"
            f"?query={quote(query)}"
            f"&max_results={max_results}"
            "&tweet.fields=created_at,lang,public_metrics"
        )
        payload = _download_json(
            endpoint,
            headers={
                "Authorization": f"Bearer {bearer_token}",
            },
        )
        items: List[RawItem] = []
        for entry in payload.get("data", []):
            post_id = str(entry.get("id", "")).strip()
            text = normalize_whitespace(str(entry.get("text", "")).replace("\n", " "))
            if not post_id or not text:
                continue
            author = username or str(self.source.get("name", "x-source"))
            title = text[:120]
            items.append(
                RawItem(
                    id=f"{slugify(str(self.source['name']))}-{post_id}",
                    source_type=str(self.source["source_type"]),
                    source_name=str(self.source["name"]),
                    title=title,
                    url=f"https://x.com/{author}/status/{post_id}",
                    published_at=str(entry.get("created_at", utc_now_iso())),
                    language=str(entry.get("lang", self.source.get("language", "en"))),
                    raw_text=text[:6000],
                    content_depth="headline",
                    body_extraction_status="x_post",
                )
            )
        return items

    def _fetch_web(self) -> List[RawItem]:
        content = _download_text(str(self.source["url"]))
        article_links = _discover_article_links(str(self.source["url"]), content)
        if not article_links:
            return [_build_landing_page_item(self.source, content)]

        items: List[RawItem] = []
        source_name = str(self.source["name"])
        for link in article_links[:5]:
            try:
                article_html = _download_text(link)
            except Exception:
                continue
            article = _extract_article(self.source, link, article_html)
            if article and not _is_navigation_page(article.title, source_name):
                items.append(article)

        if items:
            return items
        return [_build_landing_page_item(self.source, content)]


_NAV_WORDS = frozenset({
    "doing business", "federal users", "about us", "contact us", "home",
    "sitemap", "privacy policy", "terms of service", "subscribe", "advertise",
    "careers", "about the site", "site index", "accessibility", "login", "sign in",
    "community", "extended community",
})


def _is_navigation_page(title: str, source_name: str) -> bool:
    """Return True if the item looks like a site navigation page rather than an article."""
    if not title:
        return False
    # Pattern: "Page Title | Source Name" — typical for nav/category pages
    if " | " in title:
        suffix = title.split(" | ")[-1].strip().lower()
        src_lower = source_name.lower()
        if suffix in src_lower or src_lower in suffix or len(suffix) > 4 and suffix in title.lower().replace(suffix, ""):
            return True
    # Known navigation keywords
    title_lower = title.lower().strip()
    if any(nav in title_lower for nav in _NAV_WORDS):
        return True
    return False


def _download_text(url: str) -> str:
    return _download_response_text(url)


def _download_json(url: str, headers: Dict[str, str] | None = None) -> Dict[str, object]:
    return json.loads(_download_response_text(url, headers=headers))


def _download_response_text(url: str, headers: Dict[str, str] | None = None) -> str:
    request_headers = {
        "User-Agent": "emergency-intel-system/0.1",
    }
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        headers=request_headers,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="ignore")


def build_adapters(source_registry: Iterable[Dict[str, object]]) -> List[SourceAdapter]:
    return [
        SourceAdapter(source=entry)
        for entry in source_registry
        if entry.get("enabled", True)  # skip sources explicitly disabled
    ]


def _discover_article_links(base_url: str, html: str) -> List[str]:
    extractor = _HTMLLinkExtractor()
    extractor.feed(html)
    base_domain = urlparse(base_url).netloc
    candidates: List[str] = []
    seen = set()
    for href in extractor.links:
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base_domain:
            continue
        if _looks_like_article_path(parsed.path) and absolute not in seen:
            seen.add(absolute)
            candidates.append(absolute)
    return candidates


def _looks_like_article_path(path: str) -> bool:
    lowered = path.lower()
    if len(lowered) < 10:
        return False
    if lowered.endswith((".jpg", ".png", ".pdf", ".zip")):
        return False
    patterns = [
        r"/\d{4}/\d{2}/",
        r"/news/",
        r"/blog/",
        r"/article",
        r"/story",
        r"/wireless/",
        r"/projects/",
        r"/en/blog/",
        r"/the-batch/",
        r"/r/",
    ]
    if any(re.search(pattern, lowered) for pattern in patterns):
        return True
    return lowered.count("-") >= 3


def _extract_article(source: Dict[str, object], url: str, html: str) -> RawItem | None:
    title = _extract_meta_content(html, "property", "og:title") or _extract_title_tag(html) or str(source["name"])
    description = (
        _extract_meta_content(html, "property", "og:description")
        or _extract_meta_content(html, "name", "description")
        or ""
    )
    published_at = (
        _extract_meta_content(html, "property", "article:published_time")
        or _extract_meta_content(html, "name", "article:published_time")
        or utc_now_iso()
    )
    text = _extract_best_body(html)
    body = text[:5000]
    if len(body) < 160 and not description:
        return None
    raw_text = normalize_whitespace(f"{description} {body}".strip())
    return RawItem(
        id=f"{slugify(str(source['name']))}-{slugify(title)[:50]}",
        source_type=str(source["source_type"]),
        source_name=str(source["name"]),
        title=normalize_whitespace(title),
        url=url,
        published_at=published_at,
        language=str(source.get("language", "en")),
        raw_text=raw_text[:6000],
        content_depth="fulltext_candidate" if len(raw_text) >= 1200 else "summary",
        body_extraction_status="article_extracted",
    )


def _build_landing_page_item(source: Dict[str, object], html: str) -> RawItem:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    title = str(source["name"])
    text = normalize_whitespace(" ".join(parser.parts))
    return RawItem(
        id=f"{slugify(title)}-landing-page",
        source_type=str(source["source_type"]),
        source_name=title,
        title=title,
        url=str(source["url"]),
        published_at=utc_now_iso(),
        language=str(source.get("language", "en")),
        raw_text=text[:4000],
        content_depth="headline",
        body_extraction_status="landing_page",
    )


def _extract_title_tag(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return normalize_whitespace(match.group(1)) if match else ""


def _extract_meta_content(html: str, attr_name: str, attr_value: str) -> str:
    pattern = (
        rf'<meta[^>]+{attr_name}=["\']{re.escape(attr_value)}["\'][^>]+content=["\'](.*?)["\']'
        rf"|<meta[^>]+content=[\"'](.*?)[\"'][^>]+{attr_name}=[\"']{re.escape(attr_value)}[\"']"
    )
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    for group in match.groups():
        if group:
            return normalize_whitespace(group)
    return ""


def _extract_og_image(html: str, base_url: str = "") -> str:
    """Extract thumbnail URL from HTML. Priority: og:image > twitter:image > first <img>.

    Returns empty string if nothing found or URL looks like an icon/logo.
    """
    # og:image
    url = _extract_meta_content(html, "property", "og:image")
    if not url:
        url = _extract_meta_content(html, "name", "twitter:image")

    # Fallback: first <img> with a reasonable src
    if not url:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if match:
            url = match.group(1).strip()

    if not url:
        return ""

    # Resolve relative URLs
    if base_url and url.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        url = f"{parsed.scheme}://{parsed.netloc}{url}"

    # Filter out icons, tracking pixels, and tiny images
    lower = url.lower()
    skip_patterns = ("favicon", "logo", "icon", "pixel", "tracker", "1x1", "badge", "avatar")
    if any(p in lower for p in skip_patterns):
        return ""

    if not url.startswith(("http://", "https://")):
        return ""

    return url


def _sort_key_for_published_at(value: str) -> float:
    cleaned = (value or "").strip()
    if not cleaned:
        return 0.0
    try:
        return parsedate_to_datetime(cleaned).timestamp()
    except Exception:
        return 0.0


def _extract_best_body(html: str) -> str:
    candidates = [
        _extract_json_ld_article_body(html),
        _extract_tag_text(html, "article"),
        _extract_tag_text(html, "main"),
        _extract_class_pattern_text(html, "article-body"),
        _extract_class_pattern_text(html, "post-content"),
        _extract_class_pattern_text(html, "entry-content"),
        _extract_class_pattern_text(html, "story-body"),
        _extract_class_pattern_text(html, "content-body"),
        _extract_class_pattern_text(html, "article-content"),
        _extract_class_pattern_text(html, "post-body"),
    ]
    for candidate in candidates:
        cleaned = normalize_whitespace(candidate)
        if len(cleaned) >= 250:
            return cleaned

    parser = _HTMLTextExtractor()
    parser.feed(html)
    return normalize_whitespace(" ".join(parser.parts))


def _extract_tag_text(html: str, tag_name: str) -> str:
    match = re.search(rf"<{tag_name}\b[^>]*>(.*?)</{tag_name}>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    content = re.sub(r"<script\b.*?</script>", " ", match.group(1), flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<style\b.*?</style>", " ", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<[^>]+>", " ", content)
    return normalize_whitespace(content)


def _extract_class_pattern_text(html: str, class_fragment: str) -> str:
    """Extract text from a div/section whose class attribute contains class_fragment."""
    pattern = (
        rf'<(?:div|section|p)\b[^>]*class=["\'][^"\']*{re.escape(class_fragment)}[^"\']*["\'][^>]*>'
        rf'(.*?)</(?:div|section|p)>'
    )
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    content = re.sub(r"<script\b.*?</script>", " ", match.group(1), flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<style\b.*?</style>", " ", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<[^>]+>", " ", content)
    return normalize_whitespace(content)


def _extract_json_ld_article_body(html: str) -> str:
    matches = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    for block in matches:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue
        found = _search_article_body(payload)
        if found:
            return found
    return ""


def _search_article_body(payload: object) -> str:
    if isinstance(payload, dict):
        for key in ("articleBody", "description", "text"):
            value = payload.get(key)
            if isinstance(value, str) and len(normalize_whitespace(value)) >= 120:
                return normalize_whitespace(value)
        for value in payload.values():
            found = _search_article_body(value)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _search_article_body(item)
            if found:
                return found
    return ""
