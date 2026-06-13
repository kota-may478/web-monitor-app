"""スクレイピングユーティリティ"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; WebMonitorBot/1.0)"
MAX_ITEMS = 20
MAX_TEXT_LENGTH = 500
TIMEOUT_SECONDS = 15.0


def _is_safe_url(url: str) -> bool:
    """プライベートIPやlocalhostへのリクエストを防ぐ（SSRF対策）"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        if not hostname:
            return False
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            return False
        for info in infos:
            addr = info[4][0]
            try:
                ip = ipaddress.ip_address(addr)
                if not ip.is_global or ip.is_private or ip.is_loopback or ip.is_link_local:
                    return False
            except ValueError:
                return False
        return True
    except Exception:
        return False


async def scrape_site(
    url: str,
    keywords: list[str],
    css_selector: str | None = None,
) -> list[dict]:
    """
    指定URLをスクレイピングし、キーワードを含む要素を返す。

    Returns:
        [{"text": str, "url": str, "found_keywords": list[str]}]
        最大20件を返す。
    """
    results: list[dict] = []
    keywords_lower = [k.lower() for k in keywords]

    if not _is_safe_url(url):
        logger.warning("スクレイピングをブロック（プライベートIP/不正スキーム）: %s", url)
        return results

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers={"User-Agent": USER_AGENT})
            response.raise_for_status()
    except Exception as e:
        logger.warning("スクレイピング失敗 (%s): %s", url, e)
        return results

    try:
        soup = BeautifulSoup(response.text, "html.parser")
        if css_selector:
            elements = soup.select(css_selector)
        else:
            elements = [soup.body] if soup.body else []

        seen_texts: set[str] = set()
        for element in elements:
            if element is None:
                continue
            for tag in element.find_all(["p", "li", "h1", "h2", "h3", "h4", "a", "div", "span", "article"]):
                text = tag.get_text(strip=True)
                if not text or len(text) < 10:
                    continue
                if text in seen_texts:
                    continue

                text_lower = text.lower()
                found = [kw for kw, kw_lower in zip(keywords, keywords_lower) if kw_lower in text_lower]
                if not found:
                    continue

                seen_texts.add(text)
                item_url = url
                if tag.name == "a" and tag.get("href"):
                    href = tag["href"]
                    if href.startswith("http"):
                        item_url = href
                    elif href.startswith("/"):
                        from urllib.parse import urljoin

                        item_url = urljoin(url, href)

                results.append(
                    {
                        "text": text[:MAX_TEXT_LENGTH],
                        "url": item_url,
                        "found_keywords": found,
                    }
                )
                if len(results) >= MAX_ITEMS:
                    return results
    except Exception as e:
        logger.warning("HTML解析失敗 (%s): %s", url, e)

    return results
