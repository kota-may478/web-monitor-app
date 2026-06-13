"""同期版スクレイピングユーティリティ"""

import logging
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MAX_ITEMS = 20
MAX_TEXT_LENGTH = 500
TIMEOUT_SECONDS = 15.0
TAGS_TO_SCAN = ["p", "li", "h1", "h2", "h3", "h4", "a", "article", "td"]
# 助成・公募系サイトでよく出る語（Gemini提案キーワードが厳しすぎる場合のフォールバック）
FALLBACK_KEYWORDS = [
    "公募", "募集", "締切", "締め切り", "助成", "研究", "申請", "採択",
    "grant", "deadline", "fellowship", "call for",
]


def _resolve_elements(soup: BeautifulSoup, css_selector: str | None) -> list:
    """CSSセレクタで要素を取得。0件なら body 全体にフォールバックする。"""
    if css_selector:
        elements = soup.select(css_selector)
        if not elements:
            logger.warning(
                "CSSセレクタ '%s' が0件 — body全体にフォールバックします",
                css_selector,
            )
            return [soup.body] if soup.body else []
        return elements
    return [soup.body] if soup.body else []


def _collect_by_keywords(
    elements: list,
    keywords: list[str],
    base_url: str,
    seen_texts: set[str],
    results: list[dict],
) -> None:
    """キーワードを含む要素を収集する。"""
    if not keywords:
        return
    keywords_lower = [k.lower() for k in keywords]

    for element in elements:
        if element is None:
            continue
        for tag in element.find_all(TAGS_TO_SCAN):
            text = tag.get_text(strip=True)
            if not text or len(text) < 10 or text in seen_texts:
                continue

            text_lower = text.lower()
            found = [kw for kw, kw_lower in zip(keywords, keywords_lower) if kw_lower in text_lower]
            if not found:
                continue

            seen_texts.add(text)
            item_url = base_url
            if tag.name == "a" and tag.get("href"):
                href = tag["href"]
                if href.startswith("http"):
                    item_url = href
                elif href.startswith("/"):
                    item_url = urljoin(base_url, href)

            results.append(
                {
                    "text": text[:MAX_TEXT_LENGTH],
                    "url": item_url,
                    "found_keywords": found,
                }
            )
            if len(results) >= MAX_ITEMS:
                return


def _collect_headlines_and_links(
    soup: BeautifulSoup,
    base_url: str,
    seen_texts: set[str],
    results: list[dict],
) -> None:
    """キーワード一致がない場合の最終フォールバック: 見出しとリンクを収集。"""
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "a"]):
        text = tag.get_text(strip=True)
        if not text or len(text) < 10 or len(text) > 300 or text in seen_texts:
            continue
        seen_texts.add(text)
        item_url = base_url
        if tag.name == "a" and tag.get("href"):
            href = tag["href"]
            if href.startswith("http"):
                item_url = href
            elif href.startswith("/"):
                item_url = urljoin(base_url, href)

        results.append(
            {
                "text": text[:MAX_TEXT_LENGTH],
                "url": item_url,
                "found_keywords": [],
            }
        )
        if len(results) >= MAX_ITEMS:
            return


def _parse_html(
    html: str,
    url: str,
    keywords: list[str],
    css_selector: str | None,
) -> list[dict]:
    """HTMLからアイテムを抽出する。"""
    results: list[dict] = []
    seen_texts: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")
    elements = _resolve_elements(soup, css_selector)

    _collect_by_keywords(elements, keywords, url, seen_texts, results)
    if not results and keywords:
        merged = list(dict.fromkeys(keywords + FALLBACK_KEYWORDS))
        logger.info("キーワード一致0件 — フォールバックキーワードで再試行 (%s)", url)
        _collect_by_keywords(elements, merged, url, seen_texts, results)
    if not results:
        logger.info("キーワード一致0件 — 見出し・リンクを収集 (%s)", url)
        _collect_headlines_and_links(soup, url, seen_texts, results)

    return results


def scrape_site(
    url: str,
    keywords: list[str],
    css_selector: str | None = None,
) -> list[dict]:
    """
    同期版スクレイピング関数。
    backend/services/scraper.py の同期実装版。
    """
    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
    except Exception as e:
        logger.warning("スクレイピング失敗 (%s): %s", url, e)
        return []

    try:
        return _parse_html(response.text, url, keywords, css_selector)
    except Exception as e:
        logger.warning("HTML解析失敗 (%s): %s", url, e)
        return []
