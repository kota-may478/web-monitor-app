"""Pydanticモデル定義"""

import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_CRON_RE = re.compile(r"^[0-9*,\-/]+(\s+[0-9*,\-/]+){4}$")


def _validate_http_url(v: str) -> str:
    parsed = urlparse(v.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URLはhttp://またはhttps://で始まる必要があります")
    if not parsed.hostname:
        raise ValueError("無効なURLです")
    return v.strip()


class SiteProposal(BaseModel):
    url: str = Field(description="監視対象URL")
    name: str = Field(description="サイト名", max_length=200)
    description: str = Field(description="選定理由", max_length=500)
    target_keywords: list[str] = Field(description="監視するキーワード")
    css_selector: str | None = Field(default=None, description="スクレイピング対象CSSセレクタ（推定）")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)

    @field_validator("target_keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("キーワードは最大20個です")
        return v


class EmailFormat(BaseModel):
    subject_template: str = Field(description="件名テンプレート（例: [週次レポート] {{topic}} - {{date}}）", max_length=300)
    body_template: str = Field(description="本文テンプレート（{{new_items}} {{all_items}} {{scan_date}} {{topic}} を含む）", max_length=5000)


class AgentResponse(BaseModel):
    sites: list[SiteProposal] = Field(description="提案された監視サイト一覧")
    email_format: EmailFormat = Field(description="メールフォーマット")
    agent_message: str = Field(description="エージェントからの説明", max_length=1000)


class JobRequest(BaseModel):
    query: str = Field(description="調査したい内容", max_length=500)
    schedule_cron: str = Field(description="cron式（UTC基準）")
    schedule_label: str = Field(description="人間が読める頻度説明", max_length=100)
    email: str = Field(description="通知先メールアドレス")

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        v = v.strip()
        if not _CRON_RE.match(v):
            raise ValueError("無効なcron式です（例: 0 0 * * 6）")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("無効なメールアドレスです")
        return v


class JobDefinition(BaseModel):
    """
    GitHubSecretsに保存されるジョブ定義。
    gitリポジトリには保存しない。
    """

    id: str = Field(description="UUID v4")
    query: str = Field(description="調査したい内容", max_length=500)
    email: str = Field(description="通知先メールアドレス")
    schedule_cron: str = Field(description="cron式（UTC基準）")
    schedule_label: str = Field(description="人間が読める頻度説明", max_length=100)
    sites: list[SiteProposal] = Field(description="監視サイト一覧")
    email_format: EmailFormat = Field(description="メールフォーマット")
    created_at: str = Field(description="ISO8601形式の作成日時")
    active: bool = Field(default=True, description="ジョブが有効かどうか")

    @field_validator("sites")
    @classmethod
    def validate_sites(cls, v: list[SiteProposal]) -> list[SiteProposal]:
        if len(v) > 10:
            raise ValueError("監視サイトは最大10件です")
        return v


class ConfirmJobRequest(BaseModel):
    job: JobDefinition = Field(description="登録するジョブ定義")


class JobSummary(BaseModel):
    """
    ジョブ一覧取得時に返す情報。
    メールアドレス等の機密情報は含まない。
    """

    id: str = Field(description="ジョブID（UUID）")
    id8: str = Field(description="IDの先頭8文字")
    query: str = Field(description="調査内容")
    schedule_label: str = Field(description="頻度ラベル")
    site_count: int = Field(description="監視サイト数")
    created_at: str = Field(description="作成日時")
    active: bool = Field(description="ジョブが有効かどうか")


class ScanState(BaseModel):
    """
    GitHub Secretsに保存するスキャン状態。
    直近50件のみ保持する。
    """

    last_scan: str | None = Field(default=None, description="ISO8601形式の最終スキャン日時")
    items: list[dict] = Field(default_factory=list, description="スキャン結果アイテム（最大50件）")


class TestScrapeRequest(BaseModel):
    url: str = Field(description="スクレイピング対象URL")
    keywords: list[str] = Field(description="検索キーワード")
    css_selector: str | None = Field(default=None, description="CSSセレクタ", max_length=300)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return _validate_http_url(v)

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        if len(v) > 20:
            raise ValueError("キーワードは最大20個です")
        return v


class TestScrapeResponse(BaseModel):
    results: list[dict] = Field(description="スクレイピング結果")
    count: int = Field(description="結果件数")


class JobMeta(BaseModel):
    """
    gitリポジトリ (.github/job-meta/{id8}.json) に保存するジョブメタ情報。
    email はプライバシー保護のため含まない。
    """

    id: str = Field(description="UUID v4")
    query: str = Field(description="調査したい内容", max_length=500)
    schedule_cron: str = Field(description="cron式（UTC基準）")
    schedule_label: str = Field(description="人間が読める頻度説明", max_length=100)
    sites: list[SiteProposal] = Field(description="監視サイト一覧")
    email_format: EmailFormat = Field(description="メールフォーマット")
    created_at: str = Field(description="ISO8601形式の作成日時")
    active: bool = Field(default=True, description="ジョブが有効かどうか")


class JobDetail(JobMeta):
    """GET /api/jobs/{id} レスポンス — UIの編集フォーム向け"""

    email_hidden: bool = Field(default=True, description="emailはgitに保存しないため常にtrue")


class UpdateJobRequest(BaseModel):
    """PUT /api/jobs/{id} リクエスト"""

    query: str = Field(description="調査したい内容", max_length=500)
    schedule_cron: str = Field(description="cron式（UTC基準）")
    schedule_label: str = Field(description="人間が読める頻度説明", max_length=100)
    sites: list[SiteProposal] = Field(description="監視サイト一覧")
    email_format: EmailFormat = Field(description="メールフォーマット")
    email: str = Field(description="通知先メールアドレス（セキュリティのため毎回入力が必要）")
    active: bool = Field(default=True, description="ジョブが有効かどうか")

    @field_validator("schedule_cron")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        v = v.strip()
        if not _CRON_RE.match(v):
            raise ValueError("無効なcron式です（例: 0 0 * * 6）")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip()
        if not _EMAIL_RE.match(v):
            raise ValueError("無効なメールアドレスです")
        return v

    @field_validator("sites")
    @classmethod
    def validate_sites(cls, v: list[SiteProposal]) -> list[SiteProposal]:
        if len(v) > 10:
            raise ValueError("監視サイトは最大10件です")
        return v
