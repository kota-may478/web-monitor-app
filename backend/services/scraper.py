"""スクレイピングユーティリティ"""

import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; WebMonitorBot/1.0)"
MAX_ITEMS = 20
MAX_TEXT_LENGTH = 500
TIMEOUT_SECONDS = 15.0


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
