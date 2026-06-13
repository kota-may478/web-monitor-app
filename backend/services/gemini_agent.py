"""Gemini APIクライアント"""

import json
import logging
import os
import re

from google import genai
from google.genai import types

from models.schemas import AgentResponse, EmailFormat, SiteProposal
from services.url_validator import check_url_reachable

logger = logging.getLogger(__name__)

MIN_SITES = 5
MAX_SITES = 7
MAX_SEARCH_ROUNDS = 4

SEARCH_EXPANSION_HINTS: tuple[str, ...] = (
    (
        "調査テーマに最も関連する公式サイト（省庁・研究振興機構・独立行政法人など）の"
        "公募一覧・新着情報ページを Google 検索で見つけてください。"
    ),
    (
        "前回の一部URLは到達確認に失敗しました。同じテーマで別の公式公募・新着ページを"
        "Google 検索で探し、まだ提案していないサイトを追加してください。"
    ),
    (
        "検索範囲を広げてください。関連する省庁・独立行政法人・学協会・研究支援機関の"
        "公式サイトも候補に含めてください。"
    ),
    (
        "さらに検索範囲を広げてください。大学の研究支援ページ、国際的な研究費ポータル、"
        "業界団体の助成情報など、調査テーマに関連する公式情報源を探索してください。"
        "テーマに合う場合は海外の公募（英語サイト）も可です。"
    ),
)

SYSTEM_PROMPT = """あなたはWebモニタリングの専門家です。
ユーザーが定期的に確認したい情報テーマを受け取り、
そのテーマに関連する情報が掲載されているWebサイトを特定して監視計画を提案します。

Google検索ツールを使い、各URLが実在し公募・募集情報が掲載されていることを確認してから提案してください。
記憶だけでURLのパスを推測してはいけません（例: /pr/info/koubo/ のような存在しないパス）。

以下のJSON形式のみで応答してください。マークダウンのコードブロックは不要です。
{
  "sites": [
    {
      "url": "https://example.com/page",
      "name": "サイト名",
      "description": "このサイトを選んだ理由（1〜2文）",
      "target_keywords": ["キーワード1", "キーワード2"],
      "css_selector": null
    }
  ],
  "email_format": {
    "subject_template": "[週次レポート] {{topic_short}} - {{date}}",
    "body_template": "## {{topic}} 調査レポート（{{scan_date}}）\\n\\n### 🆕 新着情報\\n{{new_items}}\\n\\n### 📋 全件\\n{{all_items}}"
  },
  "agent_message": "提案の根拠や注意事項（日本語で2〜3文）"
}

要件:
- サイトは最低5件・最大7件を提案する（到達確認で除外される分を見越して多めに提案してよい）
- 監視対象は公募一覧・新着情報・募集案内など、複数の募集が掲載されるページを選ぶ
- css_selectorは常にnull
- target_keywordsはフォールバック用に短い語を5〜8個（例: 公募, 募集, 締切, 助成）
- キーワードは日本語サイトでは日本語を優先する
- email_formatのsubject_templateには {{topic_short}} を使う
- email_formatのbody_templateには {{new_items}} {{all_items}} {{scan_date}} {{topic}} を含める
- 存在しないドメインや推測URLは使わない
- 日本語の公式サイトを優先する（追加入力では指示に従い範囲を広げてよい）"""

FOLLOW_UP_SYSTEM_PROMPT = """あなたはWebモニタリングの専門家です。
追加の監視サイトだけを Google 検索で見つけ、以下のJSON形式のみで応答してください。

{
  "sites": [
    {
      "url": "https://example.com/page",
      "name": "サイト名",
      "description": "選定理由（1〜2文）",
      "target_keywords": ["キーワード1"],
      "css_selector": null
    }
  ]
}

- 既に採用済み・到達失敗のURLは再提案しない
- 記憶だけでURLを推測しない。検索で確認した公式ページのみ
- css_selectorは常にnull"""

MODEL_PRIMARY = "gemini-2.5-flash"
MODEL_FALLBACK = "gemini-2.0-flash"


def _get_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません")
    return genai.Client(api_key=api_key)


def _extract_json(text: str) -> dict:
    text = text.strip()
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if code_block_match:
        text = code_block_match.group(1).strip()
    return json.loads(text)


def _normalize_url_key(url: str) -> str:
    return url.strip().rstrip("/").lower()


async def _call_gemini(
    client: genai.Client,
    model: str,
    user_prompt: str,
    *,
    follow_up: bool = False,
) -> str:
    system_instruction = FOLLOW_UP_SYSTEM_PROMPT if follow_up else SYSTEM_PROMPT
    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    if not response.text:
        raise ValueError("Gemini APIから空のレスポンスが返されました")
    return response.text


async def _call_gemini_with_fallback(
    client: genai.Client,
    user_prompt: str,
    *,
    follow_up: bool = False,
) -> dict:
    last_error: Exception | None = None
    for model in [MODEL_PRIMARY, MODEL_FALLBACK]:
        try:
            text = await _call_gemini(
                client, model, user_prompt, follow_up=follow_up
            )
            return _extract_json(text)
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning("モデル %s: JSONパース失敗", model)
        except Exception as e:
            last_error = e
            logger.warning("モデル %s での呼び出しに失敗: %s", model, e)
    raise RuntimeError(str(last_error)) from last_error


def _build_user_prompt(
    query: str,
    schedule_label: str,
    round_idx: int,
    accepted: list[SiteProposal],
    rejected: list[str],
    needed: int,
    request_count: int,
) -> str:
    expansion = SEARCH_EXPANSION_HINTS[min(round_idx, len(SEARCH_EXPANSION_HINTS) - 1)]
    lines = [
        f"調査テーマ:\n{query}",
        f"調査頻度: {schedule_label}",
        "",
        f"【今回の目標】到達可能な監視サイトをあと少なくとも {needed} 件見つける（"
        f"今回の応答では {request_count} 件まで提案してよい）。",
        f"【検索方針】{expansion}",
    ]

    if accepted:
        lines.append("")
        lines.append("【採用済み — 重複禁止】")
        for site in accepted:
            lines.append(f"- {site.name}: {site.url}")

    if rejected:
        lines.append("")
        lines.append("【到達確認失敗 — 再提案禁止】")
        for entry in rejected[-15:]:
            lines.append(f"- {entry}")

    if round_idx > 0:
        lines.append("")
        lines.append(
            "sites には新規サイトのみ含めてください（email_format と agent_message は不要）。"
        )
    else:
        lines.append("")
        lines.append(
            "Google 検索で公式の公募・新着ページを確認し、"
            "取得可能なURLのみ返してください。"
        )

    return "\n".join(lines)


async def _validate_proposed_sites(
    raw_sites: list[dict],
    seen_urls: set[str],
) -> tuple[list[SiteProposal], list[str]]:
    valid: list[SiteProposal] = []
    rejected: list[str] = []

    for raw in raw_sites:
        if not isinstance(raw, dict):
            continue
        url = (raw.get("url") or "").strip()
        if not url:
            continue
        url_key = _normalize_url_key(url)
        if url_key in seen_urls:
            continue

        ok, final_url, err = await check_url_reachable(url)
        if not ok:
            rejected.append(f"{url} ({err})")
            continue

        final_key = _normalize_url_key(final_url)
        if final_key in seen_urls:
            continue

        try:
            site = SiteProposal.model_validate(
                {
                    **raw,
                    "url": final_url,
                    "css_selector": None,
                }
            )
        except ValueError as e:
            rejected.append(f"{url} (形式エラー: {e})")
            continue

        seen_urls.add(final_key)
        valid.append(site)

    return valid, rejected


async def _search_sites_iteratively(
    client: genai.Client,
    query: str,
    schedule_label: str,
) -> tuple[list[SiteProposal], list[str], dict, str]:
    accepted: list[SiteProposal] = []
    seen_urls: set[str] = set()
    all_rejected: list[str] = []
    email_format: dict = {}
    agent_message = ""

    for round_idx in range(MAX_SEARCH_ROUNDS):
        if len(accepted) >= MIN_SITES:
            break

        needed = MIN_SITES - len(accepted)
        request_count = min(MAX_SITES, needed + 2)
        user_prompt = _build_user_prompt(
            query,
            schedule_label,
            round_idx,
            accepted,
            all_rejected,
            needed,
            request_count,
        )
        follow_up = round_idx > 0

        logger.info(
            "サイト提案ラウンド %d/%d（採用 %d 件、あと %d 件必要）",
            round_idx + 1,
            MAX_SEARCH_ROUNDS,
            len(accepted),
            needed,
        )

        data = await _call_gemini_with_fallback(
            client, user_prompt, follow_up=follow_up
        )

        if round_idx == 0:
            email_format = data.get("email_format", {})
            agent_message = data.get("agent_message", "")

        batch_valid, batch_rejected = await _validate_proposed_sites(
            data.get("sites", []),
            seen_urls,
        )
        accepted.extend(batch_valid)
        all_rejected.extend(batch_rejected)
        logger.info(
            "ラウンド %d 結果: +%d 件採用（合計 %d 件）、%d 件除外",
            round_idx + 1,
            len(batch_valid),
            len(accepted),
            len(batch_rejected),
        )

    return accepted[:MAX_SITES], all_rejected, email_format, agent_message


def _append_agent_notes(
    agent_message: str,
    accepted_count: int,
    all_rejected: list[str],
) -> str:
    notes: list[str] = []
    if all_rejected:
        notes.append(
            f"到達確認できなかったURLを{len(all_rejected)}件除外しました: "
            + "、".join(all_rejected[:5])
            + (" 他" if len(all_rejected) > 5 else "")
        )
    if accepted_count < MIN_SITES:
        notes.append(
            f"到達可能なサイトは {accepted_count} 件でした（目標 {MIN_SITES} 件）。"
            "不足分はジョブ管理画面から手動で追加してください。"
        )
    if not notes:
        return agent_message
    suffix = "\n".join(notes)
    if agent_message:
        return f"{agent_message}\n\n※ {suffix}"
    return f"※ {suffix}"


async def analyze_and_propose(
    query: str,
    schedule_label: str,
    email: str,  # noqa: ARG001 - プライバシー保護のためGeminiには渡さない
) -> AgentResponse:
    """
    ユーザーの調査クエリを受け取り、監視サイト候補とメールフォーマットを提案する。
    メールアドレスはGeminiに渡さない（プライバシー保護）。
    """
    _ = email
    client = _get_client()

    sites, rejected, email_format_raw, agent_message = await _search_sites_iteratively(
        client, query, schedule_label
    )

    if not sites:
        raise ValueError(
            "到達可能な監視サイトを1件も特定できませんでした。"
            "調査テーマを見直すか、しばらくして再試行してください。"
        )

    agent_message = _append_agent_notes(agent_message, len(sites), rejected)

    return AgentResponse(
        sites=sites,
        email_format=EmailFormat.model_validate(email_format_raw),
        agent_message=agent_message,
    )
