# Web Monitor App

> **English first · 日本語は下に続きます**

Register what you want to track, and an LLM proposes sites to monitor. After you approve, a scheduled job scrapes the web and emails you the results — with **all sensitive data stored in GitHub Secrets**, not in git.

**Full deployment guide:** [docs/SETUP.md](docs/SETUP.md) (step-by-step, ~30–40 min)

---

## Privacy by design

- Job definitions, scan results, and email addresses live in **GitHub Secrets**
- The git repository contains only code and workflow YAML (job IDs only)
- Safe to use as a **public** repo — monitoring content is not exposed

## Tech stack

| Layer | Technology | Free tier |
|-------|------------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS | Render Static Site |
| Backend API | FastAPI (Python 3.11) + Docker | Render Web Service (750 h/mo) |
| LLM agent | Google Gemini 2.5 Flash (+ 2.0 Flash fallback) | Free tier (per-model quota; see [docs/SETUP.md §9](docs/SETUP.md#9-operations--troubleshooting)) |
| Scheduler | GitHub Actions (cron) | Unlimited (public repos) |
| Scraping | httpx + BeautifulSoup4 | — |
| Storage | GitHub Secrets | 100 entries/repo |
| Email | Resend API | 3,000 emails/month |

## Quick start (local)

**Prerequisites:** Python 3.11+, Node.js 18+, [GitHub PAT (classic)](https://github.com/settings/tokens), [Gemini API key](https://aistudio.google.com/apikey), [Resend API key](https://resend.com)

```bash
cp .env.example .env          # fill in API keys and GITHUB_REPO
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd .. && bash scripts/dev.sh
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

For first-time setup (GitHub repo, secrets, Render deploy), follow **[docs/SETUP.md](docs/SETUP.md)**.

## Deploy (overview)

1. Push to GitHub (`main`)
2. Add system secrets: `GEMINI_API_KEY`, `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, `REPO_PAT`, `RENDER_DEPLOY_HOOK_URL`
3. Deploy backend (Docker) and frontend (static) on Render
4. Pushes to `backend/**` or `frontend/**` trigger deploy via `.github/workflows/deploy.yml`

Details: [docs/SETUP.md §7](docs/SETUP.md#7-deploy-to-render) · Email test: [§8](docs/SETUP.md#8-verify-end-to-end-email-via-github-actions)

## How it works

1. User enters topic, schedule, and email in the UI
2. Gemini **searches the web** and proposes **5–7 reachable sites** (HTTP-validated; no hardcoded catalog)
3. On confirm → job JSON → GitHub Secrets; workflow `job_{id8}.yml` and `.github/job-meta/{id8}.json` are created
4. On schedule → fetch each site → **Gemini extracts relevant items** (events, grants, announcements, etc.) → diff → email → update state in Secrets

Topics are **not limited to grants** — event listings, experience programs, and general announcements work the same way.

If Gemini or page fetch fails for some sites, the report email includes a **partial-failure notice** (`一部サイトの分析に失敗`).

## Job limit

**Max 48 jobs** per repository (GitHub allows 100 secrets; ~5 system + 2 per job).

| Secret pattern | Purpose |
|----------------|---------|
| `JOB_{ID8}_DEF` | Job definition JSON |
| `JOB_{ID8}_STATE` | Scan state (last 50 items) |

## Project layout

```
web-monitor-app/
├── backend/           # FastAPI
├── frontend/          # React + Vite
├── scheduler/         # GitHub Actions scripts
├── scripts/           # dev.sh, job maintenance scripts
├── docs/SETUP.md      # Full setup guide
├── docs/OPERATIONS.md # Operations & troubleshooting
└── .github/
    ├── workflows/     # deploy.yml, job_*.yml
    └── job-meta/      # Non-sensitive job metadata (no email)
```

## License

MIT

---
---
---

# Web Monitor App（日本語）

> 上記が英語版です。このセクション以降が日本語版です。

調査したい情報を登録するだけで、LLM が監視サイトを提案し、承認後は定期実行でスクレイピング結果をメール通知するアプリです。**機密データはすべて GitHub Secrets に保存**し、git には含めません。

**詳細なセットアップ手順:** [docs/SETUP.md](docs/SETUP.md)（全7ステップ、約30〜40分）

---

## プライバシー設計

- ジョブ定義・スキャン結果・メールアドレスは **GitHub Secrets** に保存
- git リポジトリにはコードとワークフロー YAML（ジョブ ID のみ）のみ
- **public リポジトリ**でも監視内容が外部から参照できない構成

## 技術スタック

| レイヤー | 技術 | 無料枠 |
|----------|------|--------|
| フロントエンド | React 18 + Vite + Tailwind CSS | Render Static Site |
| バックエンド API | FastAPI (Python 3.11) + Docker | Render Web Service（750h/月） |
| LLM エージェント | Google Gemini 2.5 Flash（2.0 Flash フォールバック） | 無料枠（モデルごとの上限。[docs/SETUP.md §9](docs/SETUP.md#9-運用--トラブルシューティング) 参照） |
| スケジューラ | GitHub Actions (cron) | 無制限（public リポジトリ） |
| スクレイピング | httpx + BeautifulSoup4 | — |
| データ保管 | GitHub Secrets | 100 エントリ/repo |
| メール送信 | Resend API | 3,000 通/月 |

## クイックスタート（ローカル）

**前提:** Python 3.11+、Node.js 18+、[GitHub PAT (classic)](https://github.com/settings/tokens)、[Gemini APIキー](https://aistudio.google.com/apikey)、[Resend APIキー](https://resend.com)

```bash
cp .env.example .env          # APIキーと GITHUB_REPO を記入
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd .. && bash scripts/dev.sh
```

| サービス | URL |
|----------|-----|
| フロントエンド | http://localhost:5173 |
| API | http://localhost:8000 |
| API ドキュメント | http://localhost:8000/docs |

初回セットアップ（GitHub リポジトリ作成、Secrets、Render デプロイ）は **[docs/SETUP.md](docs/SETUP.md)** を参照してください。

## デプロイ（概要）

1. GitHub に push（`main`）
2. システム用 Secrets を登録: `GEMINI_API_KEY`、`RESEND_API_KEY`、`RESEND_FROM_EMAIL`、`REPO_PAT`、`RENDER_DEPLOY_HOOK_URL`
3. Render でバックエンド（Docker）とフロントエンド（Static Site）をデプロイ
4. `backend/**` または `frontend/**` への push で `.github/workflows/deploy.yml` により自動デプロイ

詳細: [docs/SETUP.md §7（日本語）](docs/SETUP.md#7-render-へのデプロイ) · メール受信テスト: [§8](docs/SETUP.md#8-エンドツーエンド確認メール受信テスト)

## 動作の流れ

1. UI で調査内容・頻度・メールアドレスを入力
2. Gemini が **Web 検索** で **5〜7 件の到達可能なサイト** を提案（HTTP 検証あり。固定カタログは使わない）
3. 承認 → ジョブ JSON を GitHub Secrets に保存、`job_{id8}.yml` と `.github/job-meta/{id8}.json` を作成
4. スケジュール実行 → 各サイトを取得 → **Gemini が関連情報を抽出**（イベント・助成金・お知らせなど） → 差分検出 → メール送信 → 状態を Secrets に更新

調査テーマは **助成金に限定されません**。イベント一覧や体験プログラムの監視も同じ仕組みで動作します。

一部サイトで Gemini API やページ取得が失敗した場合、レポートメールに **「一部サイトの分析に失敗」** の警告が付きます。

## ジョブ数の上限

リポジトリあたり **最大 48 ジョブ**（GitHub Secrets 100 個制限、システム用約 5 + ジョブあたり 2）。

| Secret 名 | 用途 |
|-----------|------|
| `JOB_{ID8}_DEF` | ジョブ定義 JSON |
| `JOB_{ID8}_STATE` | スキャン状態（直近 50 件） |

## ディレクトリ構成

```
web-monitor-app/
├── backend/           # FastAPI
├── frontend/          # React + Vite
├── scheduler/         # GitHub Actions 用スクリプト
├── scripts/           # dev.sh、ジョブメンテ用スクリプト
├── docs/SETUP.md      # 詳細セットアップガイド
├── docs/OPERATIONS.md # 運用・トラブルシューティング
└── .github/
    ├── workflows/     # deploy.yml、job_*.yml
    └── job-meta/      # 非機密のジョブメタ（メールアドレスは含まない）
```

## ライセンス

MIT
