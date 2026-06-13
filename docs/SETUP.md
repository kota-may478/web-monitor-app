# Setup & Deployment Guide

> **English first · 日本語は下に続きます**

Step-by-step instructions to deploy Web Monitor App from scratch.  
Estimated time: **30–40 minutes**.

For a quick local start, see [README.md](../README.md).

---

## Table of Contents

1. [Create a GitHub Repository](#1-create-a-github-repository)
2. [Create a GitHub Personal Access Token](#2-create-a-github-personal-access-token)
3. [Get a Google AI Studio API Key](#3-get-a-google-ai-studio-api-key)
4. [Get a Resend API Key](#4-get-a-resend-api-key)
5. [Configure `.env` and Verify Locally](#5-configure-env-and-verify-locally)
6. [Add System GitHub Secrets](#6-add-system-github-secrets)
7. [Deploy to Render](#7-deploy-to-render)
8. [Verify end-to-end (email via GitHub Actions)](#8-verify-end-to-end-email-via-github-actions)

---

## 1. Create a GitHub Repository

**Time:** ~5 min  
**Goal:** Host code and run GitHub Actions as the scheduler.

1. Open https://github.com/new
2. Repository name: `web-monitor-app`
3. Select **Public** (required for unlimited free GitHub Actions on public repos)
4. Click **Create repository**
5. Copy the remote URL and run (HTTPS or SSH):

```bash
cd ~/path/to/web-monitor-app
# HTTPS
git remote add origin https://github.com/YOUR_USERNAME/web-monitor-app.git
# or SSH
git remote add origin git@github.com:YOUR_USERNAME/web-monitor-app.git
git add .
git commit -m "feat: initial implementation"
git push -u origin main
```

**Done when:** The repository appears on GitHub. Set **default branch** to `main` if needed.

---

## 2. Create a GitHub Personal Access Token

**Time:** ~3 min  
**Goal:** Allow the backend API and `scheduler/` scripts to read and write GitHub Secrets.

> **Important:** Fine-grained tokens cannot write Actions secrets. You need a **classic** token with the **`repo`** and **`workflow`** scopes.
>
> - `repo` — read/write Secrets, repository contents
> - `workflow` — create/update `.github/workflows/*.yml` (required for job registration)

1. Open https://github.com/settings/tokens
2. Click **Generate new token (classic)** (or edit an existing token)
3. Configure:
   - Note: `web-monitor-app`
   - Expiration: your choice (or no expiration)
   - Scopes: **repo** and **workflow**
4. Click **Generate token** (or **Update token**)
5. Copy the token (`ghp_...`) if newly generated, and set it in `.env` as `GITHUB_TOKEN`

> You will not see this token again after leaving the page.

---

## 3. Get a Google AI Studio API Key

**Time:** ~2 min  
**Goal:** Power the LLM agent (Gemini 2.5 Flash free tier).

1. Open https://aistudio.google.com/apikey (sign in with Google)
2. Click **Create API key** → **Create API key in new project**
3. Copy the API key (`AIza...`)

---

## 4. Get a Resend API Key

**Time:** ~3 min  
**Goal:** Send email notifications (3,000 emails/month free).

1. Sign up at https://resend.com
2. On the **Send your first email** onboarding screen, Resend auto-generates an API key — copy it (`re_...`).  
   **No Name or Permission step is required**; that UI appears only when you create *additional* keys later under **API Keys → Create API Key**.
3. (Optional) To create a separate key later: **API Keys** → **Create API Key** → set Name / Permission as you like.

**From address:**

- For testing: `onboarding@resend.dev` (Resend demo address)
- **Limitation:** With `onboarding@resend.dev`, you can only send to the email address you signed up with until you verify your own domain.
- For production (arbitrary recipient addresses): register and verify your domain in Resend

---

## 5. Configure `.env` and Verify Locally

**Time:** ~10 min

### A. Create `.env`

```bash
cd ~/path/to/web-monitor-app
cp .env.example .env
```

Edit `.env` with your values:

| Variable | Value |
|----------|-------|
| `GEMINI_API_KEY` | From step 3 |
| `GITHUB_TOKEN` | From step 2 |
| `GITHUB_REPO` | `YOUR_USERNAME/web-monitor-app` |
| `RESEND_API_KEY` | From step 4 |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` (for testing) |
| `FRONTEND_URL` | `http://localhost:5173` |
| `VITE_API_BASE_URL` | `http://localhost:8000` |

### B. Install dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

### C. Start dev servers

```bash
cd ..
bash scripts/dev.sh
```

### D. Checklist

- [ ] http://localhost:5173 — UI loads
- [ ] http://localhost:8000/docs — API docs load
- [ ] Enter a query → **Ask LLM** → Gemini returns site proposals
- [ ] Click **Register schedule** → workflow file appears in the repo
- [ ] GitHub **Settings → Secrets and variables → Actions** shows `JOB_****_DEF` and `JOB_****_STATE`

> **Tips**
>
> - `npm install` may report dev-dependency vulnerabilities (esbuild/vite). Safe to ignore for local dev; do **not** run `npm audit fix --force`.
> - If registration fails after Secrets are saved (e.g. missing `workflow` scope), you may get orphan `JOB_*` secrets. Delete the orphan pair and retry after fixing the PAT.
> - Each retry creates a **new** job ID. Delete old orphans before re-registering the same topic.

---

## 6. Add System GitHub Secrets

**Time:** ~5 min  
**Goal:** Provide secrets for `scheduler/run_job.py` when GitHub Actions runs.

> **Add only the 4 secrets below.** Do **not** manually add `JOB_****_DEF` / `JOB_****_STATE` — those are created automatically when you register a job in the UI.

1. Open `https://github.com/YOUR_USERNAME/web-monitor-app/settings/secrets/actions`
2. Click **New repository secret** for each row:

| Name | Value |
|------|-------|
| `RESEND_API_KEY` | Resend API key (step 4) |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` or your verified address |
| `REPO_PAT` | **Same** classic PAT as step 2 (`ghp_...`). **Cannot** use names starting with `GITHUB_` — GitHub rejects them (`GITHUB_TOKEN` is also reserved). |
| `RENDER_DEPLOY_HOOK_URL` | Skip until step 7A (GitHub does not accept empty values) |

> **Naming note:** `.env` / Render use `GITHUB_TOKEN`. GitHub repository Secrets use `REPO_PAT` for the **same token value**.

---

## 7. Deploy to Render

**Time:** ~15 min  
**Goal:** Host the API and frontend on Render’s free tier.

### A. Backend (Web Service)

1. Sign up at https://render.com (GitHub login)
2. **New +** → **Web Service** → select `web-monitor-app`
3. Settings:
   - Name: `web-monitor-app-backend`
   - Root Directory: `backend`
   - Runtime: **Docker**
   - Instance Type: **Free**
4. Environment variables:

| Key | Value |
|-----|-------|
| `GEMINI_API_KEY` | Step 3 |
| `GITHUB_TOKEN` | Step 2 (classic PAT). **OK on Render** — the `GITHUB_` prefix ban applies only to GitHub repository Secrets, not Render env vars. |
| `GITHUB_REPO` | `YOUR_USERNAME/web-monitor-app` |
| `RESEND_API_KEY` | Step 4 |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` |
| `FRONTEND_URL` | Planned frontend URL (update in step 7C to the **actual** URL after deploy) |
| `API_KEY` | Random secret for API authentication. Generate with `openssl rand -hex 32`. If unset, auth is disabled. |

5. **Deploy Web Service** and note the URL (e.g. `https://web-monitor-app-backend.onrender.com`)
6. **Settings → Deploy Hook** → copy URL → add as `RENDER_DEPLOY_HOOK_URL` in GitHub Secrets (step 6)

### B. Frontend (Static Site)

1. **New +** → **Static Site** → same repository
2. Settings:
   - Name: `web-monitor-app` (or any name; see note below)
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist` (relative to Root Directory — **not** `frontend/dist`)
3. Environment variables:
   - `VITE_API_BASE_URL` = backend URL from step A (e.g. `https://web-monitor-app-backend.onrender.com`)
   - `VITE_API_KEY` = Same value as `API_KEY`. Bundled into the frontend at build time.
4. **Deploy Static Site** and note the **actual** URL shown on the dashboard

> **Render URL note:** If `web-monitor-app.onrender.com` is taken, Render assigns a suffix (e.g. `https://web-monitor-app-032r.onrender.com`). Always use the URL Render displays — not the name you typed.

### C. Update backend CORS

1. Backend service → **Environment** → set `FRONTEND_URL` to the **actual** Static Site URL from step B
2. Choose **Save and deploy** (not **Save only** — the running container must restart to pick up the new value)

---

## 8. Verify end-to-end (email via GitHub Actions)

**Time:** ~5 min  
**Goal:** Confirm the monitor job runs on schedule and sends email.

**Prerequisites:** Steps 6–7 complete, at least one job registered (workflow `job_*.yml` exists), system secrets including `REPO_PAT` set.

1. **Notification email:** With `onboarding@resend.dev`, the job's notification address must be the **email you used to sign up for Resend**. Other addresses will fail until you verify a custom domain.
2. Open GitHub → **Actions** → select your monitor workflow (e.g. `job_2a03f3ee`)
3. Click **Run workflow** → **Run workflow** (manual `workflow_dispatch` — no need to wait for Saturday)
4. Wait for the run to finish (green check). Open the run log if it fails.
5. Check your inbox for the report email.

**What a successful run does:** scrape sites → detect new items → send email via Resend → update `JOB_****_STATE`.

**If email fails:** check Actions log for Resend errors; confirm `RESEND_API_KEY`, `RESEND_FROM_EMAIL`, and recipient address.

---

## All done

| Environment | URL |
|-------------|-----|
| Local | http://localhost:5173 |
| Production | Your Render Static Site URL (e.g. `https://web-monitor-app-032r.onrender.com`) |

> **Note:** Render free web services sleep after 15 minutes of inactivity. The first request may take 30–50 seconds. GitHub Actions scheduling is unaffected.

---
---
---

# セットアップ・デプロイガイド（日本語）

> 上記が英語版です。このセクション以降が日本語版です。

Web Monitor App をゼロからデプロイするための手順です。  
所要時間の目安: **30〜40分**

ローカルだけ試す場合は [README.md](../README.md) も参照してください。

---

## 目次

1. [GitHubリポジトリの作成](#1-githubリポジトリの作成)
2. [GitHub Personal Access Token の作成](#2-github-personal-access-token-の作成)
3. [Google AI Studio APIキーの取得](#3-google-ai-studio-apiキーの取得)
4. [Resend APIキーの取得](#4-resend-apiキーの取得)
5. [`.env` の設定とローカル動作確認](#5-env-の設定とローカル動作確認)
6. [GitHub Secrets にシステム用Secretsを追加](#6-github-secrets-にシステム用secretsを追加)
7. [Render へのデプロイ](#7-render-へのデプロイ)
8. [エンドツーエンド確認（メール受信テスト）](#8-エンドツーエンド確認メール受信テスト)

---

## 1. GitHubリポジトリの作成

**所要時間:** 約5分  
**目的:** コードのホスティングと GitHub Actions スケジューラ基盤の用意

1. https://github.com/new にアクセス
2. Repository name: `web-monitor-app`
3. **Public** を選択（public リポジトリで GitHub Actions が無制限無料）
4. 「Create repository」をクリック
5. 表示された URL をコピーして以下を実行（HTTPS または SSH）:

```bash
cd ~/path/to/web-monitor-app
# HTTPS
git remote add origin https://github.com/【ユーザー名】/web-monitor-app.git
# または SSH
git remote add origin git@github.com:【ユーザー名】/web-monitor-app.git
git add .
git commit -m "feat: initial implementation"
git push -u origin main
```

**完了確認:** GitHub 上にリポジトリが表示されること。必要なら **default branch** を `main` に設定。

---

## 2. GitHub Personal Access Token の作成

**所要時間:** 約3分  
**目的:** バックエンド API と `scheduler/` から GitHub Secrets を読み書きする

> **重要:** fine-grained トークンは Actions Secrets の書き込みに非対応です。**classic** トークンで **`repo`** と **`workflow`** スコープが必須です。
>
> - `repo` — Secrets の読み書き、リポジトリ内容の更新
> - `workflow` — `.github/workflows/*.yml` の作成・更新（ジョブ登録に必要）

1. https://github.com/settings/tokens にアクセス
2. 「Generate new token (classic)」をクリック（または既存トークンを編集）
3. 設定:
   - Note: `web-monitor-app`
   - Expiration: 任意（または無期限）
   - Scopes: **repo** と **workflow** にチェック
4. 「Generate token」（または「Update token」）をクリック
5. 新規作成時はトークン（`ghp_...`）をコピーし、`.env` の `GITHUB_TOKEN` に設定

---

## 3. Google AI Studio APIキーの取得

**所要時間:** 約2分  
**目的:** LLM エージェント（Gemini 2.5 Flash 無料枠）の利用

1. https://aistudio.google.com/apikey にアクセス（Google アカウントでログイン）
2. 「Create API key」→「Create API key in new project」をクリック
3. 生成された APIキー（`AIza...`）をコピー

---

## 4. Resend APIキーの取得

**所要時間:** 約3分  
**目的:** メール通知の送信（月 3,000 通まで無料）

1. https://resend.com でサインアップ
2. **Send your first email** のオンボーディング画面で APIキーが自動表示される — それをコピー（`re_...`）。  
   **Name や Permission の設定は不要**です（追加キーを **API Keys → Create API Key** から作る場合のみ表示されます）。
3. （任意）後から別キーを作る場合: **API Keys** → **Create API Key** → Name / Permission を設定

**送信元メールアドレス:**

- テスト時: `onboarding@resend.dev`（Resend のデモアドレス）
- **制限:** `onboarding@resend.dev` では、独自ドメインを認証するまで **サインアップ時のメールアドレス宛てにしか送信できません**
- 本番運用（任意のアドレスへ通知）: Resend に独自ドメインを登録・認証する

---

## 5. `.env` の設定とローカル動作確認

**所要時間:** 約10分

### A. `.env` を作成

```bash
cd ~/path/to/web-monitor-app
cp .env.example .env
```

`.env` に以下を設定:

| 変数 | 値 |
|------|-----|
| `GEMINI_API_KEY` | 手順3で取得した値 |
| `GITHUB_TOKEN` | 手順2で取得した値 |
| `GITHUB_REPO` | `【ユーザー名】/web-monitor-app` |
| `RESEND_API_KEY` | 手順4で取得した値 |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev`（テスト時） |
| `FRONTEND_URL` | `http://localhost:5173` |
| `VITE_API_BASE_URL` | `http://localhost:8000` |

### B. 依存パッケージのインストール

```bash
# バックエンド
cd backend
pip install -r requirements.txt

# フロントエンド
cd ../frontend
npm install
```

### C. 開発サーバーの起動

```bash
cd ..
bash scripts/dev.sh
```

### D. 動作確認チェックリスト

- [ ] http://localhost:5173 — UI が表示される
- [ ] http://localhost:8000/docs — API ドキュメントが表示される
- [ ] 調査クエリを入力 →「LLMに調査させる」→ Gemini から提案が返る
- [ ] 「登録する」→ リポジトリにワークフローファイルが追加される
- [ ] GitHub **Settings → Secrets and variables → Actions** に `JOB_****_DEF` と `JOB_****_STATE` が追加されている

> **補足**
>
> - `npm install` の脆弱性警告（esbuild/vite）は開発用のみで、ローカル開発では無視してよい。`npm audit fix --force` は実行しない。
> - 登録が途中で失敗すると（例: `workflow` スコープ不足）、`JOB_*` Secrets だけ残ることがある。PAT 修正後にゴミを削除してから再登録する。
> - 再登録のたびに **新しいジョブ ID** が作られる。同じ内容を登録し直す前に、古い `JOB_*` を削除する。

---

## 6. GitHub Secrets にシステム用Secretsを追加

**所要時間:** 約5分  
**目的:** GitHub Actions 実行時に `scheduler/run_job.py` が使う Secrets を登録

> **手動で追加するのは下記4つのみ。** `JOB_****_DEF` / `JOB_****_STATE` は UI でジョブ登録したときに **自動作成** されるので、ここでは追加しない。

1. `https://github.com/【ユーザー名】/web-monitor-app/settings/secrets/actions` にアクセス
2. **New repository secret** から1件ずつ追加:

| 名前 | 値 |
|------|-----|
| `RESEND_API_KEY` | 手順4の Resend APIキー |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` または確認済みアドレス |
| `REPO_PAT` | 手順2と **同じ** classic PAT（`ghp_...`）。`GITHUB_` で始まる名前は GitHub 側で登録不可 |
| `RENDER_DEPLOY_HOOK_URL` | 手順7Aまで省略可（空欄は登録できない） |

> **名前の使い分け:** `.env` / Render では `GITHUB_TOKEN`、GitHub リポジトリ Secrets では **同じ値** を `REPO_PAT` として登録する。

---

## 7. Render へのデプロイ

**所要時間:** 約15分  
**目的:** API とフロントエンドを Render 無料枠でホスティング

### A. バックエンド（Web Service）

1. https://render.com でサインアップ（GitHub 連携）
2. 「New +」→「Web Service」→ `web-monitor-app` を選択
3. 設定:
   - Name: `web-monitor-app-backend`
   - Root Directory: `backend`
   - Runtime: **Docker**
   - Instance Type: **Free**
4. 環境変数:

| キー | 値 |
|------|-----|
| `GEMINI_API_KEY` | 手順3 |
| `GITHUB_TOKEN` | 手順2（classic PAT）。**Render では `GITHUB_TOKEN` で正しい**（`GITHUB_` 禁止は GitHub リポジトリ Secrets のみ） |
| `GITHUB_REPO` | `【ユーザー名】/web-monitor-app` |
| `RESEND_API_KEY` | 手順4 |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` |
| `FRONTEND_URL` | フロントの予定 URL（手順7Cで **実際の URL** に更新） |
| `API_KEY` | API 認証用のランダムシークレット。`openssl rand -hex 32` で生成。未設定の場合は認証無効。 |

5. **Deploy Web Service** → URL をメモ（例: `https://web-monitor-app-backend.onrender.com`）
6. **Settings → Deploy Hook** の URL を `RENDER_DEPLOY_HOOK_URL` として GitHub Secrets に追加（手順6）

### B. フロントエンド（Static Site）

1. 「New +」→「Static Site」→ 同じリポジトリ
2. 設定:
   - Name: `web-monitor-app`（任意。下記 URL 注意）
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`（Root Directory からの相対パス。**`frontend/dist` ではない**）
3. 環境変数:
   - `VITE_API_BASE_URL` = 手順Aのバックエンド URL
   - `VITE_API_KEY` = `API_KEY` と同じ値。フロントエンドのビルド時に埋め込まれる。
4. **Deploy Static Site** → ダッシュボードに表示された **実際の URL** をメモ

> **Render URL について:** `web-monitor-app.onrender.com` が取れない場合、`-032r` などのサフィックスが付く（例: `https://web-monitor-app-032r.onrender.com`）。入力した Name ではなく、**Render が表示した URL** を使う。

### C. バックエンドの CORS 更新

1. バックエンドサービス → **Environment** → `FRONTEND_URL` を手順Bの **実際の** Static Site URL に設定
2. **Save and deploy** を選択（**Save only** では実行中コンテナに反映されない）

---

## 8. エンドツーエンド確認（メール受信テスト）

**所要時間:** 約5分  
**目的:** 監視ジョブが動き、メールが届くことを確認する。

**前提:** 手順6・7完了、ジョブ登録済み（`job_*.yml` あり）、`REPO_PAT` などシステム Secrets 設定済み。

1. **通知先メール:** `onboarding@resend.dev` 利用時は、ジョブの通知先を **Resend サインアップ時のメールアドレス** にする（他アドレスは独自ドメイン認証まで送信不可）
2. GitHub → **Actions** → 監視ワークフロー（例: `job_2a03f3ee`）を開く
3. **Run workflow** → **Run workflow**（土曜を待たず手動実行可能）
4. 実行が成功（緑のチェック）するまで待つ。失敗時はログを確認
5. 受信トレイでレポートメールを確認

**成功時の流れ:** スクレイピング → 差分検出 → Resend でメール送信 → `JOB_****_STATE` 更新

**メールが届かない場合:** Actions ログの Resend エラーを確認。`RESEND_API_KEY`・`RESEND_FROM_EMAIL`・通知先アドレスを再確認。

---

## セットアップ完了

| 環境 | URL |
|------|-----|
| ローカル | http://localhost:5173 |
| 本番 | Render Static Site の実際の URL（例: `https://web-monitor-app-032r.onrender.com`） |

> **注意:** Render 無料 Web サービスは 15 分間アクセスがないとスリープします。初回リクエストに 30〜50 秒かかることがあります。GitHub Actions のスケジューラは Render に依存しないため影響を受けません。
