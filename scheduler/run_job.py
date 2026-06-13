"""
GitHub Actionsから呼び出されるメインスクリプト。

実行フロー:
1. secrets_store.get_job_def() でジョブ定義を取得
2. secrets_store.get_job_state() で前回スキャン状態を取得
3. 各サイトを取得し Gemini で関連情報を抽出（GEMINI_API_KEY 未設定時はキーワードマッチにフォールバック）
4. 全サイトの結果をフラットなリストにまとめる
5. diff_checker.detect_new_items() で新規アイテムを検出
6. mailer.send_report() でメール送信
7. diff_checker.merge_items() で新状態を構築
8. secrets_store.save_job_state() で状態をSecretsに保存
"""

import logging
import os
import sys
from datetime import datetime, timezone

import diff_checker
import gemini_extractor
import mailer
import scraper
import secrets_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _scrape_site_with_llm(
    query: str,
    site: dict,
    scan_time: datetime,
) -> list[dict]:
    """Gemini でページから関連情報を抽出する。"""
    url = site.get("url", "")
    site_name = site.get("name", url)
    css_selector = site.get("css_selector")

    logger.info("LLM抽出: %s (%s)", site_name, url)
    page_text = scraper.fetch_page_text(url, css_selector)
    if not page_text:
        logger.warning("  → ページテキスト取得失敗")
        return []

    items = gemini_extractor.extract_items(
        query=query,
        page_url=url,
        site_name=site_name,
        page_text=page_text,
        scan_date=scan_time,
    )
    logger.info("  → %d件抽出", len(items))
    return items


def _scrape_site_with_keywords(site: dict) -> list[dict]:
    """GEMINI_API_KEY 未設定時のフォールバック（キーワードマッチ）。"""
    url = site.get("url", "")
    keywords = site.get("target_keywords", [])
    css_selector = site.get("css_selector")
    logger.info("キーワードマッチ: %s", url)
    items = scraper.scrape_site(url, keywords, css_selector)
    logger.info("  → %d件取得", len(items))
    return items


def main() -> None:
    """メイン実行関数"""
    job_id = os.environ.get("JOB_ID", "")
    from_email = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    use_llm = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    scan_time = datetime.now(timezone.utc)

    if use_llm:
        logger.info("抽出モード: Gemini LLM")
    else:
        logger.warning(
            "GEMINI_API_KEY 未設定 — キーワードマッチモードで実行します。"
            "GitHub Secrets に GEMINI_API_KEY を追加してください。"
        )

    # 1. ジョブ定義取得
    try:
        job_def = secrets_store.get_job_def()
        query = job_def.get("query", "")
        logger.info("ジョブ定義を取得: %s", query[:80])
    except Exception as e:
        logger.error("ジョブ定義の取得に失敗: %s", e)
        sys.exit(0)

    # 2. 前回状態取得
    try:
        previous_state = secrets_store.get_job_state()
        previous_items = previous_state.get("items", [])
        logger.info("前回状態: %d件のアイテム", len(previous_items))
    except Exception as e:
        logger.error("前回状態の取得に失敗: %s", e)
        previous_items = []

    # 3. 各サイトをスクレイピング / LLM抽出
    all_current_items: list[dict] = []
    sites = job_def.get("sites", [])
    for site in sites:
        try:
            if use_llm:
                items = _scrape_site_with_llm(query, site, scan_time)
            else:
                items = _scrape_site_with_keywords(site)
            all_current_items.extend(items)
        except Exception as e:
            logger.error("サイト処理失敗 (%s): %s", site.get("url", ""), e)

    logger.info("全サイト合計: %d件のアイテム", len(all_current_items))
    if not all_current_items:
        if use_llm:
            logger.warning(
                "抽出結果が0件です。監視サイトのURLが適切か、"
                "ページに調査テーマに関連する公募情報があるか確認してください。"
            )
        else:
            logger.warning(
                "スクレイピング結果が0件です。GEMINI_API_KEY の設定を推奨します。"
            )

    # 4-5. 差分検出
    try:
        new_items = diff_checker.detect_new_items(all_current_items, previous_items)
        logger.info("新規アイテム: %d件", len(new_items))
    except Exception as e:
        logger.error("差分検出に失敗: %s", e)
        new_items = []

    # 6. メール送信
    try:
        email_format = job_def.get("email_format", {})
        mailer.send_report(
            recipient_email=job_def.get("email", ""),
            from_email=from_email,
            subject_template=email_format.get(
                "subject_template", "[レポート] {{topic_short}} - {{date}}"
            ),
            body_template=email_format.get("body_template", "{{new_items}}\n{{all_items}}"),
            topic=query,
            new_items=new_items,
            all_items=all_current_items,
        )
    except Exception as e:
        logger.error("メール送信に失敗: %s", e)

    # 7-8. 状態保存
    try:
        merged_items = diff_checker.merge_items(all_current_items, previous_items)
        new_state = {
            "last_scan": scan_time.isoformat(),
            "items": merged_items,
        }
        if job_id:
            saved = secrets_store.save_job_state(job_id, new_state)
            if saved:
                logger.info("状態を保存しました（%d件）", len(merged_items))
            else:
                logger.error("状態の保存に失敗しました")
    except Exception as e:
        logger.error("状態保存に失敗: %s", e)

    logger.info("ジョブ実行完了")
    sys.exit(0)


if __name__ == "__main__":
    main()
