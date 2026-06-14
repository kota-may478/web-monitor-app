"""Gemini API によるページ内容の関連情報抽出（スケジューラ用・同期）"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL_PRIMARY = "gemini-2.5-flash"
MODEL_FALLBACK = "gemini-2.0-flash"

MAX_PAGE_CHARS = 6000
MAX_RETRIES = 3
DEFAULT_INTER_REQUEST_DELAY_SEC = 4.0

SYSTEM_PROMPT = """あなたはWebページから調査テーマに関連する情報を抽出する専門家です。

ユーザーが監視したい調査テーマ（query）と、Webページのテキストが与えられます。
ページに実際に書かれている情報のみを根拠に、テーマに合致する情報を抽出してください。

query の内容に応じて、例えば次のような情報を対象にします:
- イベント・体験・見学会・搭乗・参加募集
- 助成金・研究費・公募・申請案内
- 新着お知らせ・制度変更・申込期間の告知

以下のJSON形式のみで応答してください。マークダウンのコードブロックは不要です。
{
  "items": [
    {
      "title": "情報のタイトル（イベント名・制度名など）",
      "summary": "概要（対象者・日時・場所・費用・申込方法など、1〜3文、ページの記述に基づく）",
      "url": "詳細ページのURL（ページ内にあれば。なければ空文字）",
      "deadline": "締切日または開催日（YYYY-MM-DD形式。不明ならnull）",
      "relevance": "調査テーマとの関連（1文）"
    }
  ]
}

ルール:
- ページに存在しない情報を推測・創作しない
- 調査テーマに明らかに無関係なものは含めない
- query に期日・地域・無料・対象者などの条件があれば、それを満たす（または満たす可能性がある）ものを優先する
- すでに終了し、今後の参加・申込機会がないものだけの記載は含めない
- 該当情報がなければ {"items": []} を返す
- 最大10件まで
- url はページテキストまたはソースURLに含まれるものだけ使用する"""

BATCH_SYSTEM_PROMPT = SYSTEM_PROMPT + """

複数サイト分のページが与えられる場合、各 item に次のフィールドも必ず含めてください:
- "source_site": 入力の監視サイト名と一致させる
- "source_url": 入力のソースURLと一致させる
全サイト合計で最大20件まで。"""


@dataclass
class ExtractionResult:
    items: list[dict]
    api_failed: bool
    quota_exhausted: bool = False


def batch_extraction_enabled() -> bool:
    """デフォルト ON — 1ジョブあたり Gemini を1回だけ呼ぶ（無料枠節約）。"""
    value = os.environ.get("GEMINI_BATCH_EXTRACTION", "true").strip().lower()
    return value not in ("0", "false", "no", "off")


def inter_request_delay_sec() -> float:
    raw = os.environ.get("GEMINI_REQUEST_DELAY_SEC", "").strip()
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return DEFAULT_INTER_REQUEST_DELAY_SEC


def _extract_json(text: str) -> dict:
    text = text.strip()
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block_match:
        text = code_block_match.group(1).strip()
    return json.loads(text)


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")
    return genai.Client(api_key=api_key)


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    return min(30.0, 5.0 * (2**attempt))


def _call_gemini(client: genai.Client, model: str, user_prompt: str, *, system_prompt: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
        ),
    )
    if not response.text:
        raise ValueError("Gemini APIから空のレスポンスが返されました")
    return response.text


def _call_gemini_with_retry(
    client: genai.Client,
    model: str,
    user_prompt: str,
    *,
    system_prompt: str,
) -> str:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return _call_gemini(client, model, user_prompt, system_prompt=system_prompt)
        except Exception as exc:
            last_error = exc
            if _is_rate_limit_error(exc) and attempt < MAX_RETRIES - 1:
                delay = _retry_delay_seconds(exc, attempt)
                logger.warning(
                    "モデル %s: 429 — %.1f秒後にリトライ (%d/%d)",
                    model,
                    delay,
                    attempt + 1,
                    MAX_RETRIES,
                )
                time.sleep(delay)
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Gemini呼び出しに失敗しました")


def _generate_with_models(
    client: genai.Client,
    user_prompt: str,
    *,
    system_prompt: str,
) -> tuple[str | None, Exception | None, bool]:
    """Returns (text, last_error, quota_exhausted)."""
    last_error: Exception | None = None
    quota_exhausted = False

    for model in [MODEL_PRIMARY, MODEL_FALLBACK]:
        try:
            text = _call_gemini_with_retry(
                client, model, user_prompt, system_prompt=system_prompt
            )
            return text, None, False
        except Exception as exc:
            logger.warning("モデル %s での抽出に失敗: %s", model, exc)
            last_error = exc
            if _is_rate_limit_error(exc):
                quota_exhausted = True
                # 無料枠枯渇時は別モデルへの切替は無意味なことが多い
                break

    return None, last_error, quota_exhausted


def _truncate_page_text(page_text: str) -> str:
    text = page_text.strip()
    if len(text) <= MAX_PAGE_CHARS:
        return text
    return text[:MAX_PAGE_CHARS] + "\n…（以降省略）"


def _format_item_text(item: dict) -> str:
    """差分検出・メール表示用のテキストを組み立てる。"""
    parts: list[str] = []
    title = (item.get("title") or "").strip()
    if title:
        parts.append(title)
    deadline = item.get("deadline")
    if deadline:
        parts.append(f"締切: {deadline}")
    summary = (item.get("summary") or "").strip()
    if summary:
        parts.append(summary)
    relevance = (item.get("relevance") or "").strip()
    if relevance and relevance not in summary:
        parts.append(f"({relevance})")
    return " — ".join(parts) if parts else "（無題）"


def _normalize_raw_item(
    raw: dict,
    default_url: str,
    default_site: str,
) -> dict | None:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    summary = (raw.get("summary") or "").strip()
    item_url = (raw.get("url") or "").strip() or (raw.get("source_url") or "").strip() or default_url
    site_name = (raw.get("source_site") or "").strip() or default_site
    source_url = (raw.get("source_url") or "").strip() or default_url
    deadline = raw.get("deadline")
    if deadline is not None:
        deadline = str(deadline).strip() or None

    item = {
        "title": title,
        "summary": summary,
        "url": item_url,
        "deadline": deadline,
        "relevance": (raw.get("relevance") or "").strip(),
        "source_site": site_name,
        "source_url": source_url,
    }
    item["text"] = _format_item_text(item)
    return item


def _parse_items_from_response(
    data: dict,
    *,
    default_url: str,
    default_site: str,
    max_items: int,
) -> list[dict]:
    results: list[dict] = []
    for raw in data.get("items", [])[:max_items]:
        if not isinstance(raw, dict):
            continue
        normalized = _normalize_raw_item(raw, default_url, default_site)
        if normalized:
            results.append(normalized)
    return results


def extract_items(
    query: str,
    page_url: str,
    site_name: str,
    page_text: str,
    scan_date: datetime | None = None,
) -> ExtractionResult:
    """
    ページテキストから調査テーマに関連する情報を Gemini で抽出する（1サイト・1 API呼び出し）。
    """
    if not page_text.strip():
        return ExtractionResult(items=[], api_failed=False)

    if scan_date is None:
        scan_date = datetime.now(timezone.utc)
    scan_date_str = scan_date.strftime("%Y-%m-%d")

    user_prompt = (
        f"調査日: {scan_date_str}\n"
        f"調査テーマ（query）:\n{query}\n\n"
        f"監視サイト名: {site_name}\n"
        f"ソースURL: {page_url}\n\n"
        f"--- ページテキスト ---\n{_truncate_page_text(page_text)}\n--- ここまで ---"
    )

    client = _get_client()
    text, last_error, quota_exhausted = _generate_with_models(
        client, user_prompt, system_prompt=SYSTEM_PROMPT
    )

    if text is None:
        logger.error("Gemini抽出に失敗: %s", last_error)
        return ExtractionResult(items=[], api_failed=True, quota_exhausted=quota_exhausted)

    try:
        data = _extract_json(text)
    except json.JSONDecodeError as exc:
        logger.error("Gemini応答のJSONパースに失敗: %s", exc)
        return ExtractionResult(items=[], api_failed=True)

    results = _parse_items_from_response(
        data, default_url=page_url, default_site=site_name, max_items=10
    )

    if not results and len(page_text.strip()) > 300:
        logger.info(
            "Gemini抽出: %s → 0件（ページテキスト %d 文字 — テーマ条件に合う情報がない可能性）",
            page_url,
            len(page_text),
        )
    else:
        logger.info("Gemini抽出: %s → %d件", page_url, len(results))
    return ExtractionResult(items=results, api_failed=False)


def extract_items_batch(
    query: str,
    pages: list[dict],
    scan_date: datetime | None = None,
) -> ExtractionResult:
    """
    複数サイトを1回の Gemini 呼び出しでまとめて抽出する（API消費を1回に抑える）。

    pages: [{"site_name", "page_url", "page_text"}, ...]
    """
    if not pages:
        return ExtractionResult(items=[], api_failed=False)

    if scan_date is None:
        scan_date = datetime.now(timezone.utc)
    scan_date_str = scan_date.strftime("%Y-%m-%d")

    sections: list[str] = []
    for index, page in enumerate(pages, start=1):
        site_name = page.get("site_name", "")
        page_url = page.get("page_url", "")
        page_text = _truncate_page_text(page.get("page_text", ""))
        sections.append(
            f"### サイト {index}\n"
            f"監視サイト名: {site_name}\n"
            f"ソースURL: {page_url}\n"
            f"--- ページテキスト ---\n{page_text}\n--- ここまで ---"
        )

    user_prompt = (
        f"調査日: {scan_date_str}\n"
        f"調査テーマ（query）:\n{query}\n\n"
        f"以下は {len(pages)} 件の監視サイトです。各サイトから関連情報を抽出してください。\n\n"
        + "\n\n".join(sections)
    )

    client = _get_client()
    logger.info("Geminiバッチ抽出: %dサイトを1回のAPI呼び出しで処理", len(pages))
    text, last_error, quota_exhausted = _generate_with_models(
        client, user_prompt, system_prompt=BATCH_SYSTEM_PROMPT
    )

    if text is None:
        logger.error("Geminiバッチ抽出に失敗: %s", last_error)
        return ExtractionResult(items=[], api_failed=True, quota_exhausted=quota_exhausted)

    try:
        data = _extract_json(text)
    except json.JSONDecodeError as exc:
        logger.error("Geminiバッチ応答のJSONパースに失敗: %s", exc)
        return ExtractionResult(items=[], api_failed=True)

    results = _parse_items_from_response(
        data,
        default_url=pages[0].get("page_url", ""),
        default_site=pages[0].get("site_name", ""),
        max_items=20,
    )
    logger.info("Geminiバッチ抽出: 合計 %d件", len(results))
    return ExtractionResult(items=results, api_failed=False)
