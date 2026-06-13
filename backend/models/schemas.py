"""Pydanticモデル定義"""

from pydantic import BaseModel, Field


class SiteProposal(BaseModel):
    url: str = Field(description="監視対象URL")
    name: str = Field(description="サイト名")
    description: str = Field(description="選定理由")
    target_keywords: list[str] = Field(description="監視するキーワード")
    css_selector: str | None = Field(default=None, description="スクレイピング対象CSSセレクタ（推定）")


class EmailFormat(BaseModel):
    subject_template: str = Field(description="件名テンプレート（例: [週次レポート] {{topic}} - {{date}}）")
    body_template: str = Field(description="本文テンプレート（{{new_items}} {{all_items}} {{scan_date}} {{topic}} を含む）")


class AgentResponse(BaseModel):
    sites: list[SiteProposal] = Field(description="提案された監視サイト一覧")
    email_format: EmailFormat = Field(description="メールフォーマット")
    agent_message: str = Field(description="エージェントからの説明")


class JobRequest(BaseModel):
    query: str = Field(description="調査したい内容")
    schedule_cron: str = Field(description="cron式（UTC基準）")
    schedule_label: str = Field(description="人間が読める頻度説明")
    email: str = Field(description="通知先メールアドレス")


class JobDefinition(BaseModel):
    """
    GitHubSecretsに保存されるジョブ定義。
    gitリポジトリには保存しない。
    """

    id: str = Field(description="UUID v4")
    query: str = Field(description="調査したい内容")
    email: str = Field(description="通知先メールアドレス")
    schedule_cron: str = Field(description="cron式（UTC基準）")
    schedule_label: str = Field(description="人間が読める頻度説明")
    sites: list[SiteProposal] = Field(description="監視サイト一覧")
    email_format: EmailFormat = Field(description="メールフォーマット")
    created_at: str = Field(description="ISO8601形式の作成日時")
    active: bool = Field(default=True, description="ジョブが有効かどうか")


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
    css_selector: str | None = Field(default=None, description="CSSセレクタ")


class TestScrapeResponse(BaseModel):
    results: list[dict] = Field(description="スクレイピング結果")
    count: int = Field(description="結果件数")
