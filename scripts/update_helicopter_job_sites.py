"""ジョブ 241c45f0 の監視サイトを更新する（一回限りの運用スクリプト）"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "backend"))

from models.schemas import EmailFormat, JobDefinition, SiteProposal  # noqa: E402
from services import github_service  # noqa: E402

JOB_ID = "241c45f0-fbee-416e-8a5e-f8e608722e7c"
QUERY = "ヘリコプター体験搭乗の無料イベント情報（東京近郊）"

SITES: list[SiteProposal] = [
    SiteProposal(
        url="https://www.noevirgreen.or.jp/environment/sky/",
        name="ノエビアグリーン財団 空の教室（ヘリコプター体験）",
        description="東京ヘリポートでのヘリコプター体験フライト。募集・開催の告知が掲載される公式ページ。",
        target_keywords=["ヘリコプター", "体験", "搭乗", "無料", "東京", "募集", "空の教室", "イベント"],
        css_selector=None,
    ),
    SiteProposal(
        url="https://www.noevirgreen.or.jp/foundation/topics/",
        name="ノエビアグリーン財団 トピックス",
        description="ヘリコプター体験フライトの募集締切・活動レポートなど新着告知。",
        target_keywords=["ヘリコプター", "体験", "募集", "締切", "東京", "開催", "お知らせ"],
        css_selector=None,
    ),
    SiteProposal(
        url="https://www.noevirgreen.or.jp/foundation/information/index.html",
        name="ノエビアグリーン財団 インフォメーション",
        description="財団のお知らせ一覧。体験イベントの募集情報が掲載される。",
        target_keywords=["ヘリコプター", "体験", "募集", "お知らせ", "イベント", "東京"],
        css_selector=None,
    ),
    SiteProposal(
        url="https://rikuzi-chousadan.com/sdfmuseum/gsdf_rikkunland.html",
        name="陸上自衛隊広報センター りっくんランド（練馬）",
        description="東京都練馬区で実施される自衛隊ヘリコプター体験搭乗イベントの情報。防衛省公式サイトはボット遮断のため、到達可能な情報ページを監視。",
        target_keywords=["ヘリコプター", "体験搭乗", "りっくんランド", "練馬", "東京", "募集", "UH-1J"],
        css_selector=None,
    ),
    SiteProposal(
        url="https://www.aeromuseum.or.jp/event/",
        name="航空科学博物館 イベント情報",
        description="成田の航空博物館イベント一覧。ヘリコプター関連イベントや航空体験の告知がある。",
        target_keywords=["ヘリコプター", "航空", "イベント", "体験", "無料", "搭乗", "博物館"],
        css_selector=None,
    ),
    SiteProposal(
        url="https://www.gotokyo.org/jp/event/index.html",
        name="GO TOKYO イベントカレンダー",
        description="東京都の公式観光イベント情報。首都圏の体験イベントを横断的に確認できる。",
        target_keywords=["イベント", "体験", "東京", "ヘリコプター", "無料", "参加", "開催"],
        css_selector=None,
    ),
    SiteProposal(
        url="https://www.walkerplus.com/event_list/",
        name="ウォーカープラス イベント一覧",
        description="全国のイベント情報ポータル。関東の体験・乗り物イベントの新着を拾える。",
        target_keywords=["イベント", "体験", "ヘリコプター", "無料", "東京", "千葉", "埼玉", "搭乗"],
        css_selector=None,
    ),
]


def main() -> None:
    email = os.environ.get("JOB_UPDATE_EMAIL", "kota-fujimoto@ieee.org")
    job = JobDefinition(
        id=JOB_ID,
        query=QUERY,
        email=email,
        schedule_cron="0 0 * * 6",
        schedule_label="毎週土曜日 9:00 JST",
        sites=SITES,
        email_format=EmailFormat(
            subject_template="[週次レポート] {{topic_short}} - {{date}}",
            body_template=(
                "## {{topic}} 調査レポート（{{scan_date}}）\n\n"
                "### 🆕 新着情報\n{{new_items}}\n\n"
                "### 📋 全件\n{{all_items}}"
            ),
        ),
        created_at="2026-06-13T09:03:13.400Z",
        active=True,
    )
    if not github_service.update_job(job):
        print("ジョブ更新に失敗しました", file=sys.stderr)
        sys.exit(1)
    print(f"更新完了: {JOB_ID}（監視サイト {len(SITES)} 件）")


if __name__ == "__main__":
    main()
