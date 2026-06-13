"""提案URLの到達確認"""

import logging

import httpx

from services.scraper import is_safe_url

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT_SECONDS = 12.0


async def check_url_reachable(url: str) -> tuple[bool, str, str]:
    """
    URLが取得可能か確認する。

    Returns:
        (成功, 最終URL, エラー理由)
    """
    url = url.strip()
    if not is_safe_url(url):
        return False, url, "安全でないURL（内部ネットワーク等）"

    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        ) as client:
            response = await client.head(url, headers=headers)
            if response.status_code >= 400:
                response = await client.get(url, headers=headers)
            response.raise_for_status()
            final_url = str(response.url)
            return True, final_url, ""
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        logger.info("URL到達確認失敗 (%s): HTTP %s", url, status)
        return False, url, f"HTTP {status}"
    except httpx.RequestError as e:
        logger.info("URL到達確認失敗 (%s): %s", url, e)
        return False, url, str(e) or "接続失敗"
    except Exception as e:
        logger.warning("URL到達確認エラー (%s): %s", url, e)
        return False, url, str(e)
