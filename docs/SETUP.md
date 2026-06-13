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

---

## 1. Create a GitHub Repository

**Time:** ~5 min  
**Goal:** Host code and run GitHub Actions as the scheduler.

1. Open https://github.com/new
2. Repository name: `web-monitor-app`
3. Select **Public** (required for unlimited free GitHub Actions on public repos)
4. Click **Create repository**
5. Copy the remote URL and run:

```bash
cd ~/path/to/web-monitor-app
git remote add origin https://github.com/YOUR_USERNAME/web-monitor-app.git
git add .
git commit -m "feat: initial implementation"
git push -u origin main
```

**Done when:** The repository appears on GitHub.

---

## 2. Create a GitHub Personal Access Token

**Time:** ~3 min  
**Goal:** Allow the backend API and `scheduler/` scripts to read and write GitHub Secrets.

> **Important:** Fine-grained tokens cannot write Actions secrets. You need a **classic** token with the `repo` scope.

1. Open https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Configure:
   - Note: `web-monitor-app`
   - Expiration: your choice (or no expiration)
   - Scopes: **repo** (selects all sub-scopes)
4. Click **Generate token**
5. Copy the token (`ghp_...`) and store it securely

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
2. Go to **API Keys** → **Create API Key**
3. Configure:
   - Name: `web-monitor-app`
   - Permission: Full access
4. Copy the key (`re_...`)

**From address:**

- For testing: `onboarding@resend.dev` (Resend demo address)
- For production: register your own domain in Resend

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

---

## 6. Add System GitHub Secrets

**Time:** ~5 min  
**Goal:** Provide secrets for `scheduler/run_job.py` when GitHub Actions runs.

1. Open `https://github.com/YOUR_USERNAME/web-monitor-app/settings/secrets/actions`
2. Add these repository secrets:

| Name | Value |
|------|-------|
| `RESEND_API_KEY` | Resend API key (step 4) |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` or your verified address |
| `GITHUB_PAT` | GitHub PAT (step 2). **Not** `GITHUB_TOKEN` — that name is reserved. |
| `RENDER_DEPLOY_HOOK_URL` | Leave empty for now; add after step 7 |

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
| `GITHUB_TOKEN` | Step 2 |
| `GITHUB_REPO` | `YOUR_USERNAME/web-monitor-app` |
| `RESEND_API_KEY` | Step 4 |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` |
| `FRONTEND_URL` | Update after frontend deploy |

5. **Create Web Service** and note the URL (e.g. `https://web-monitor-app-backend.onrender.com`)
6. **Settings → Deploy Hook** → copy URL → add as `RENDER_DEPLOY_HOOK_URL` in GitHub Secrets (step 6)

### B. Frontend (Static Site)

1. **New +** → **Static Site** → same repository
2. Settings:
   - Name: `web-monitor-app-frontend`
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`
3. Environment variable:
   - `VITE_API_BASE_URL` = backend URL from step A
4. **Create Static Site** and note the URL

### C. Update backend CORS

On the backend service → **Environment** → set `FRONTEND_URL` to the frontend URL → **Save Changes**

---

## All done

| Environment | URL |
|-------------|-----|
| Local | http://localhost:5173 |
| Production | `https://web-monitor-app-frontend.onrender.com` (your URL) |

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

---

## 1. GitHubリポジトリの作成

**所要時間:** 約5分  
**目的:** コードのホスティングと GitHub Actions スケジューラ基盤の用意

1. https://github.com/new にアクセス
2. Repository name: `web-monitor-app`
3. **Public** を選択（public リポジトリで GitHub Actions が無制限無料）
4. 「Create repository」をクリック
5. 表示された URL をコピーして以下を実行:

```bash
cd ~/path/to/web-monitor-app
git remote add origin https://github.com/【ユーザー名】/web-monitor-app.git
git add .
git commit -m "feat: initial implementation"
git push -u origin main
```

**完了確認:** GitHub 上にリポジトリが表示されること

---

## 2. GitHub Personal Access Token の作成

**所要時間:** 約3分  
**目的:** バックエンド API と `scheduler/` から GitHub Secrets を読み書きする

> **重要:** fine-grained トークンは Actions Secrets の書き込みに非対応です。**classic** トークンで `repo` スコープが必須です。

1. https://github.com/settings/tokens にアクセス
2. 「Generate new token (classic)」をクリック
3. 設定:
   - Note: `web-monitor-app`
   - Expiration: 任意（または無期限）
   - Scopes: **repo**（配下が全選択される）
4. 「Generate token」をクリック
5. 表示されたトークン（`ghp_...`）をコピーして安全に保管

> このページを離れるとトークンは二度と表示されません。

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
2. 「API Keys」→「Create API Key」
3. 設定:
   - Name: `web-monitor-app`
   - Permission: Full access
4. 生成されたキー（`re_...`）をコピー

**送信元メールアドレス:**

- テスト時: `onboarding@resend.dev`（Resend のデモアドレス）
- 本番運用時: Resend に独自ドメインを登録することを推奨

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

---

## 6. GitHub Secrets にシステム用Secretsを追加

**所要時間:** 約5分  
**目的:** GitHub Actions 実行時に `scheduler/run_job.py` が使う Secrets を登録

1. `https://github.com/【ユーザー名】/web-monitor-app/settings/secrets/actions` にアクセス
2. 以下のリポジトリ Secrets を追加:

| 名前 | 値 |
|------|-----|
| `RESEND_API_KEY` | 手順4の Resend APIキー |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` または確認済みアドレス |
| `GITHUB_PAT` | 手順2の PAT（`GITHUB_TOKEN` は予約名のため不可） |
| `RENDER_DEPLOY_HOOK_URL` | 手順7で取得（今は空で可） |

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
| `GITHUB_TOKEN` | 手順2 |
| `GITHUB_REPO` | `【ユーザー名】/web-monitor-app` |
| `RESEND_API_KEY` | 手順4 |
| `RESEND_FROM_EMAIL` | `onboarding@resend.dev` |
| `FRONTEND_URL` | フロントエンドデプロイ後に更新 |

5. 「Create Web Service」→ URL をメモ（例: `https://web-monitor-app-backend.onrender.com`）
6. **Settings → Deploy Hook** の URL を `RENDER_DEPLOY_HOOK_URL` として GitHub Secrets に追加（手順6）

### B. フロントエンド（Static Site）

1. 「New +」→「Static Site」→ 同じリポジトリ
2. 設定:
   - Name: `web-monitor-app-frontend`
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Publish Directory: `dist`
3. 環境変数:
   - `VITE_API_BASE_URL` = 手順Aのバックエンド URL
4. 「Create Static Site」→ URL をメモ

### C. バックエンドの CORS 更新

バックエンドサービス → **Environment** → `FRONTEND_URL` をフロントエンド URL に更新 → **Save Changes**

---

## セットアップ完了

| 環境 | URL |
|------|-----|
| ローカル | http://localhost:5173 |
| 本番 | `https://web-monitor-app-frontend.onrender.com`（あなたの URL） |

> **注意:** Render 無料 Web サービスは 15 分間アクセスがないとスリープします。初回リクエストに 30〜50 秒かかることがあります。GitHub Actions のスケジューラは Render に依存しないため影響を受けません。
