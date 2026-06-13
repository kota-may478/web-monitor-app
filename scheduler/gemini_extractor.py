"""Gemini API によるページ内容の関連情報抽出（スケジューラ用・同期）"""

import json
import logging
import os
import re
from datetime import datetime, timezone

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

MODEL_PRIMARY = "gemini-2.5-flash"
MODEL_FALLBACK = "gemini-2.0-flash"

SYSTEM_PROMPT = """あなたはWebページから助成金・研究費・会議参加費などの申請情報を抽出する専門家です。

ユーザーが監視したい調査テーマ（query）と、Webページのテキストが与えられます。
ページに実際に書かれている情報のみを根拠に、調査テーマに関連する申請・公募・募集情報を抽出してください。

以下のJSON形式のみで応答してください。マークダウンのコードブロックは不要です。
{
  "items": [
    {
      "title": "公募・制度の名称",
      "summary": "対象者・概要・金額など（1〜3文、ページの記述に基づく）",
      "url": "詳細ページのURL（ページ内にあれば。なければ空文字）",
      "deadline": "締切日（YYYY-MM-DD形式。不明ならnull）",
      "relevance": "調査テーマとの関連（1文）"
    }
  ]
}

ルール:
- ページに存在しない情報を推測・創作しない
- 調査テーマに明らかに無関係なものは含めない
- 調査テーマに「○か月以内に締切」などの条件があれば、その条件を満たすものだけを含める
- 該当情報がなければ {"items": []} を返す
- 最大10件まで
- url はページテキストまたはソースURLに含まれるものだけ使用する"""


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


def _call_gemini(client: genai.Client, model: str, user_prompt: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
        ),
    )
    if not response.text:
        raise ValueError("Gemini APIから空のレスポンスが返されました")
    return response.text


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


def _normalize_raw_item(raw: dict, source_url: str, site_name: str) -> dict | None:
    title = (raw.get("title") or "").strip()
    if not title:
        return None
    summary = (raw.get("summary") or "").strip()
    item_url = (raw.get("url") or "").strip() or source_url
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


def extract_items(
    query: str,
    page_url: str,
    site_name: str,
    page_text: str,
    scan_date: datetime | None = None,
) -> list[dict]:
    """
    ページテキストから調査テーマに関連する情報を Gemini で抽出する。

    Returns:
        [{"title", "summary", "url", "deadline", "text", "source_site", ...}]
    """
    if not page_text.strip():
        return []

    if scan_date is None:
        scan_date = datetime.now(timezone.utc)
    scan_date_str = scan_date.strftime("%Y-%m-%d")

    user_prompt = (
        f"調査日: {scan_date_str}\n"
        f"調査テーマ（query）:\n{query}\n\n"
        f"監視サイト名: {site_name}\n"
        f"ソースURL: {page_url}\n\n"
        f"--- ページテキスト ---\n{page_text}\n--- ここまで ---"
    )

    client = _get_client()
    text: str | None = None
    last_error: Exception | None = None

    for model in [MODEL_PRIMARY, MODEL_FALLBACK]:
        try:
            text = _call_gemini(client, model, user_prompt)
            break
        except Exception as e:
            logger.warning("モデル %s での抽出に失敗: %s", model, e)
            last_error = e

    if text is None:
        logger.error("Gemini抽出に失敗: %s", last_error)
        return []

    try:
        data = _extract_json(text)
    except json.JSONDecodeError as e:
        logger.error("Gemini応答のJSONパースに失敗: %s", e)
        return []

    results: list[dict] = []
    for raw in data.get("items", [])[:10]:
        if not isinstance(raw, dict):
            continue
        normalized = _normalize_raw_item(raw, page_url, site_name)
        if normalized:
            results.append(normalized)

    if not results and len(page_text.strip()) > 300:
        logger.info(
            "Gemini抽出: %s → 0件（ページテキスト %d 文字 — テーマ条件に合う公募がない可能性）",
            page_url,
            len(page_text),
        )
    else:
        logger.info("Gemini抽出: %s → %d件", page_url, len(results))
    return results
