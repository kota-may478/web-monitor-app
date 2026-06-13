"""Resend APIメール送信"""

import html
import logging
import os
from datetime import datetime, timezone

import resend

logger = logging.getLogger(__name__)


def render_template(template: str, **kwargs: object) -> str:
    """
    {{key}} 形式のプレースホルダーを kwargs の値で置換する。
    対応キー: topic, date, scan_date, new_items, all_items
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
        return "<p>（新着なし）</p>"

    lines = ["<ul>"]
    for item in items:
        text = html.escape(item.get("text", "")[:200])
        url = html.escape(item.get("url", ""))
        if url:
            lines.append(f'  <li><a href="{url}">{text}</a></li>')
        else:
            lines.append(f"  <li>{text}</li>")
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

    subject = render_template(
        subject_template,
        topic=topic,
        date=date_str,
        scan_date=scan_date,
        new_items=new_items,
        all_items=all_items,
    )
    body = render_template(
        body_template,
        topic=topic,
        date=date_str,
        scan_date=scan_date,
        new_items=new_items,
        all_items=all_items,
    )

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
