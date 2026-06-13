"""
GitHub Actionsから呼び出されるメインスクリプト。

実行フロー:
1. secrets_store.get_job_def() でジョブ定義を取得
2. secrets_store.get_job_state() で前回スキャン状態を取得
3. ジョブ定義の各サイトに対してscraper.scrape_site()を実行
4. 全サイトの結果をフラットなリストにまとめる
5. diff_checker.detect_new_items() で新規アイテムを検出
6. mailer.send_report() でメール送信
7. diff_checker.merge_items() で新状態を構築
8. secrets_store.save_job_state() で状態をSecretsに保存
9. 成功/失敗をログ出力して終了
"""

import logging
import os
import sys
from datetime import datetime, timezone

import diff_checker
import mailer
import scraper
import secrets_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """メイン実行関数"""
    job_id = os.environ.get("JOB_ID", "")
    from_email = os.environ.get("RESEND_FROM_EMAIL", "onboarding@resend.dev")

    # 1. ジョブ定義取得
    try:
        job_def = secrets_store.get_job_def()
        logger.info("ジョブ定義を取得: %s", job_def.get("query", ""))
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

    # 3. 各サイトをスクレイピング
    all_current_items: list[dict] = []
    sites = job_def.get("sites", [])
    for site in sites:
        try:
            url = site.get("url", "")
            keywords = site.get("target_keywords", [])
            css_selector = site.get("css_selector")
            logger.info("スクレイピング: %s", url)
            items = scraper.scrape_site(url, keywords, css_selector)
            all_current_items.extend(items)
            logger.info("  → %d件取得", len(items))
        except Exception as e:
            logger.error("スクレイピング失敗 (%s): %s", site.get("url", ""), e)

    logger.info("全サイト合計: %d件のアイテム", len(all_current_items))
    if not all_current_items:
        logger.warning(
            "スクレイピング結果が0件です。CSSセレクタの不一致やキーワードの厳しすぎる"
            "設定が原因の可能性があります。ジョブ管理画面でサイト設定を見直してください。"
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
            subject_template=email_format.get("subject_template", "[レポート] {{topic}}"),
            body_template=email_format.get("body_template", "{{new_items}}\n{{all_items}}"),
            topic=job_def.get("query", ""),
            new_items=new_items,
            all_items=all_current_items,
        )
    except Exception as e:
        logger.error("メール送信に失敗: %s", e)

    # 7-8. 状態保存
    try:
        merged_items = diff_checker.merge_items(all_current_items, previous_items)
        new_state = {
            "last_scan": datetime.now(timezone.utc).isoformat(),
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
