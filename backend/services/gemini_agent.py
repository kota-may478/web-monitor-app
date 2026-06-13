"""Gemini APIクライアント"""

import json
import logging
import os
import re

from google import genai
from google.genai import types

from models.schemas import AgentResponse, EmailFormat, SiteProposal

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """あなたはWebモニタリングの専門家です。
ユーザーが定期的に確認したい情報テーマを受け取り、
そのテーマに関連する情報が掲載されているWebサイトを特定して監視計画を提案します。

以下のJSON形式のみで応答してください。マークダウンのコードブロックは不要です。
{
  "sites": [
    {
      "url": "https://example.com/page",
      "name": "サイト名",
      "description": "このサイトを選んだ理由（1〜2文）",
      "target_keywords": ["キーワード1", "キーワード2"],
      "css_selector": "main .content"
    }
  ],
  "email_format": {
    "subject_template": "[週次レポート] {{topic}} - {{date}}",
    "body_template": "## {{topic}} 調査レポート（{{scan_date}}）\\n\\n### 🆕 新着情報\\n{{new_items}}\\n\\n### 📋 全件\\n{{all_items}}"
  },
  "agent_message": "提案の根拠や注意事項（日本語で2〜3文）"
}

要件:
- サイトは3〜7件を提案する
- css_selectorはページ構造を実際に確認できた場合のみ設定し、不明・不確実な場合は必ずnullにする（誤ったセレクタは0件になる）
- target_keywordsはユーザーの長文をそのまま使わず、各サイトのページに実際に出現しそうな短い語を5〜8個選ぶ（例: 公募, 募集, 締切, 助成, 研究, 申請）
- キーワードは日本語サイトでは日本語を優先する
- email_formatのbody_templateには {{new_items}} {{all_items}} {{scan_date}} {{topic}} を含める
- 日本語のサイトを優先して提案する"""

MODEL_PRIMARY = "gemini-2.5-flash"
MODEL_FALLBACK = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    """Gemini APIクライアントを返す"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")
    return genai.Client(api_key=api_key)


def _extract_json(text: str) -> dict:
    """レスポンステキストからJSONを抽出してパースする"""
    text = text.strip()
    # マークダウンのコードブロックを除去
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block_match:
        text = code_block_match.group(1).strip()
    return json.loads(text)


async def _call_gemini(client: genai.Client, model: str, user_prompt: str) -> str:
    """Gemini APIを呼び出してテキストレスポンスを返す"""
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        ),
    )
    if not response.text:
        raise ValueError("Gemini APIから空のレスポンスが返されました")
    return response.text


async def analyze_and_propose(
    query: str,
    schedule_label: str,
    email: str,  # noqa: ARG001 - プライバシー保護のためGeminiには渡さない
) -> AgentResponse:
    """
    ユーザーの調査クエリを受け取り、監視サイト候補とメールフォーマットを提案する。
  メールアドレスはGeminiに渡さない（プライバシー保護）。
    """
    _ = email  # 未使用（プライバシー保護）
    client = _get_client()
    user_prompt = f"調査テーマ: {query}\n調査頻度: {schedule_label}"

    text: str | None = None
    last_error: Exception | None = None

    for model in [MODEL_PRIMARY, MODEL_FALLBACK]:
        try:
            text = await _call_gemini(client, model, user_prompt)
            break
        except Exception as e:
            logger.warning("モデル %s での呼び出しに失敗: %s", model, e)
            last_error = e

    if text is None:
        raise RuntimeError(str(last_error)) from last_error

    try:
        data = _extract_json(text)
    except json.JSONDecodeError as e:
        raise ValueError("LLMの応答を解析できませんでした") from e

    return AgentResponse(
        sites=[SiteProposal.model_validate(s) for s in data.get("sites", [])],
        email_format=EmailFormat.model_validate(data.get("email_format", {})),
        agent_message=data.get("agent_message", ""),
    )
