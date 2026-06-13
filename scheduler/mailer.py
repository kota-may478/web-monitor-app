"""Resend APIメール送信"""

import html
import logging
import os
from datetime import datetime, timezone

import resend

logger = logging.getLogger(__name__)


def topic_short(topic: str, max_len: int = 60) -> str:
    """件名用: 改行を除き先頭行を最大 max_len 文字に切り詰める。"""
    first_line = topic.replace("\r\n", "\n").replace("\r", "\n").split("\n")[0].strip()
    collapsed = " ".join(first_line.split())
    if not collapsed:
        return "（無題）"
    if len(collapsed) > max_len:
        return collapsed[: max_len - 1] + "…"
    return collapsed


def sanitize_email_subject(subject: str) -> str:
    """Resend は subject フィールドに改行を許可しない。"""
    flattened = subject.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return " ".join(flattened.split()).strip()


def render_template(template: str, **kwargs: object) -> str:
    """
    {{key}} 形式のプレースホルダーを kwargs の値で置換する。
    対応キー: topic, topic_short, date, scan_date, new_items, all_items
    """
    result = template
    for key, value in kwargs.items():
        placeholder = "{{" + key + "}}"
        if key in ("new_items", "all_items") and isinstance(value, list):
            replacement = format_items_as_html(value)
        else:
            replacement = html.escape(str(value)) if value is not None else ""
        result = result.replace(placeholder, replacement)
    return result


def format_items_as_html(items: list[dict]) -> str:
    """
    スキャン結果アイテムをHTMLのulリストに変換する。
    各アイテムに url が含まれる場合はリンクにする。
    アイテムが0件の場合は "<p>（新着なし）</p>" を返す。
    """
    if not items:
        return (
            "<p>（該当なし — 調査テーマに関連する情報は見つかりませんでした。"
            "監視サイトのURLを見直すか、次回のスケジュール実行をお待ちください）</p>"
        )

    lines = ["<ul>"]
    for item in items:
        title = html.escape((item.get("title") or item.get("text", ""))[:200])
        summary = html.escape((item.get("summary") or "")[:300])
        deadline = item.get("deadline")
        url = html.escape(item.get("url", ""))
        source = html.escape(item.get("source_site", ""))

        label = title
        if deadline:
            label += f" <span style='color:#666'>（締切: {html.escape(str(deadline))}）</span>"

        inner = f'<a href="{url}">{label}</a>' if url else label
        if summary:
            inner += f"<br><span style='color:#555;font-size:0.9em'>{summary}</span>"
        if source:
            inner += f"<br><span style='color:#999;font-size:0.8em'>出典: {source}</span>"
        lines.append(f"  <li>{inner}</li>")
    lines.append("</ul>")
    return "\n".join(lines)


def send_report(
    recipient_email: str,
    from_email: str,
    subject_template: str,
    body_template: str,
    topic: str,
    new_items: list[dict],
    all_items: list[dict],
) -> bool:
    """
    Resend APIでHTMLメールを送信する。
    環境変数 RESEND_API_KEY から APIキーを読み込む。
    送信失敗時は False を返す（例外を外に出さない）。
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY が設定されていません")
        return False

    now = datetime.now(timezone.utc)
    scan_date = now.strftime("%Y-%m-%d %H:%M UTC")
    date_str = now.strftime("%Y-%m-%d")

    template_kwargs = {
        "topic": topic,
        "topic_short": topic_short(topic),
        "date": date_str,
        "scan_date": scan_date,
        "new_items": new_items,
        "all_items": all_items,
    }
    subject = sanitize_email_subject(
        render_template(subject_template, **template_kwargs)
    )
    body = render_template(body_template, **template_kwargs)

    # プレーンテキストを簡易HTMLに変換
    if not body.strip().startswith("<"):
        body = body.replace("\n", "<br>")

    try:
        resend.api_key = api_key
        resend.Emails.send(
            {
                "from": from_email,
                "to": [recipient_email],
                "subject": subject,
                "html": body,
            }
        )
        logger.info("メール送信成功: %s", recipient_email)
        return True
    except Exception as e:
        logger.exception("メール送信失敗: %s", e)
        return False
