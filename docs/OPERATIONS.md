# Operations & Troubleshooting

> **English first · 日本語は下に続きます**

Day-2 operations for Web Monitor App after [SETUP.md](SETUP.md) is complete.

---

## Gemini API usage

Each scheduled run calls Gemini **once per monitored site** (primary model `gemini-2.5-flash`, fallback `gemini-2.0-flash` on failure).

| Factor | Impact |
|--------|--------|
| Sites per job | 5–7 typical |
| Runs per day | Cron schedule + manual **Run workflow** |
| Quota | **Per model** on Google AI Studio free tier — limits change; check [AI Studio usage](https://aistudio.google.com/) |

**Tips**

- Avoid repeated manual runs on the same day while debugging — you can exhaust the daily quota quickly.
- If logs show `429 RESOURCE_EXHAUSTED`, wait until the quota resets or upgrade the API plan.
- Site proposal (`/api/agent/propose`) also uses Gemini + Google Search — separate from scheduled extraction.

---

## Partial analysis failures

When page fetch or Gemini extraction fails for one or more sites, the report email includes:

> **一部サイトの分析に失敗しました**（APIエラー・ページ取得失敗等）

Failed site names are listed. Results from successful sites are still included. An empty result with failures means the report may be **incomplete**, not necessarily “no matching items.”

Check the GitHub Actions log for lines like `Gemini抽出に失敗` or `ページテキスト取得失敗`.

---

## Choosing monitor URLs

Site proposal uses **Google Search + HTTP reachability checks**. Manual edits should follow the same rules:

| Situation | Guidance |
|-----------|----------|
| Government sites blocking bots | `mod.go.jp` etc. often return **403** from GitHub Actions. Use an alternative official page that is reachable (e.g. a museum or foundation mirror). |
| Redirects to wrong content | Verify the final URL returns **200** and is a **listing page**, not a single article. Example: GO TOKYO events use `/ja/travel-directory/...`, not legacy `/jp/event/...` paths. |
| JavaScript-only pages | Scraper uses httpx + BeautifulSoup — heavily JS-rendered pages may return little text. Prefer static HTML listing pages. |

Test locally:

```bash
cd scheduler
python -c "import scraper; print(len(scraper.fetch_page_text('https://example.com/') or ''))"
```

---

## Email templates

Placeholders for `subject_template` / `body_template`:

| Placeholder | Description |
|-------------|-------------|
| `{{topic}}` | Full query (may contain newlines) |
| `{{topic_short}}` | First line, max 60 chars — **use in subject** |
| `{{date}}` | `YYYY-MM-DD` |
| `{{scan_date}}` | `YYYY-MM-DD HH:MM UTC` |
| `{{new_items}}` | New items since last run (HTML) |
| `{{all_items}}` | All items this run (HTML) |

Resend rejects newline characters in the subject — always use `{{topic_short}}` in `subject_template`, not `{{topic}}`.

---

## Updating an existing job

Job definitions live in GitHub Secrets (`JOB_{ID8}_DEF`). Non-sensitive metadata (sites, schedule, templates — **no email**) is also stored in `.github/job-meta/{id8}.json`.

To change sites or templates without re-registering from the UI:

1. Copy `scripts/update_helicopter_job_sites.py` as a template.
2. Set `JOB_ID`, `QUERY`, and `SITES`.
3. Set notification email via `JOB_UPDATE_EMAIL` in `.env` (defaults in script if unset).
4. Run from repo root:

```bash
python scripts/update_your_job_sites.py
```

This calls `github_service.update_job()` — updates Secrets, workflow YAML, and job-meta in one step.

---

## job-meta files

| Location | Contents |
|----------|----------|
| `JOB_{ID8}_DEF` (Secret) | Full job JSON including email |
| `.github/job-meta/{id8}.json` (git) | Query, sites, schedule, templates — **no email** |

If job-meta is missing for an old job, the scheduler still works from Secrets only. Re-saving the job via API or an update script recreates job-meta.

---

## Useful log messages

| Log | Meaning |
|-----|---------|
| `抽出モード: Gemini LLM` | Normal LLM extraction path |
| `GEMINI_API_KEY 未設定` | Falls back to keyword matching (less accurate) |
| `一部サイトの分析に失敗` | Partial failure — see email warning |
| `抽出結果が0件` | No items extracted; check URLs and theme relevance |
| `JOB_STATE_JSON` empty | State secret missing — first run starts with empty history |

---
---
---

# 運用・トラブルシューティング（日本語）

> 上記が英語版です。このセクション以降が日本語版です。

[SETUP.md](SETUP.md) 完了後の運用向けメモです。

---

## Gemini API の消費量

スケジュール実行では、監視サイト **1 件あたり Gemini を 1 回** 呼び出します（主モデル `gemini-2.5-flash`、失敗時は `gemini-2.0-flash` にフォールバック）。

| 要因 | 影響 |
|------|------|
| サイト数 | 通常 5〜7 件 |
| 1 日の実行回数 | cron + 手動 **Run workflow** |
| 無料枠 | Google AI Studio の **モデルごと** の上限 — [利用状況](https://aistudio.google.com/) で確認 |

**注意**

- デバッグで同日に手動実行を繰り返すと、無料枠を使い切りやすい。
- ログに `429 RESOURCE_EXHAUSTED` が出たら、枠のリセットを待つかプランを見直す。
- UI のサイト提案（`/api/agent/propose`）も Gemini + Google 検索を使う（スケジュール実行とは別カウント）。

---

## 一部サイトの分析失敗

ページ取得または Gemini 抽出に失敗したサイトがあると、レポートメール先頭に次の警告が付きます。

> **一部サイトの分析に失敗しました**（APIエラー・ページ取得失敗等）

失敗したサイト名が列挙されます。成功したサイトの結果はそのまま含まれます。0 件かつ警告ありの場合は「該当なし」ではなく **結果が不完全** な可能性があります。

GitHub Actions ログで `Gemini抽出に失敗` や `ページテキスト取得失敗` を確認してください。

---

## 監視 URL の選び方

サイト提案は **Google 検索 + HTTP 到達確認** です。手動で URL を直す場合も同様の基準で選んでください。

| 状況 | 対処 |
|------|------|
| 官公庁サイトがボット遮断 | `mod.go.jp` などは GitHub Actions から **403** になりやすい。到達できる別の公式ページ（博物館・財団のミラーなど）を使う。 |
| リダイレクト先が別コンテンツ | 最終 URL が **200** で、単一記事ではなく **一覧ページ** か確認する。例: GO TOKYO は `/ja/travel-directory/...`（`/jp/event/...` の旧パスは不適切）。 |
| JavaScript 依存のページ | httpx + BeautifulSoup のため、JS 描画のみのページはテキストが少ない。静的 HTML の一覧ページを優先。 |

ローカル確認:

```bash
cd scheduler
python -c "import scraper; print(len(scraper.fetch_page_text('https://example.com/') or ''))"
```

---

## メールテンプレート

`subject_template` / `body_template` のプレースホルダー:

| プレースホルダー | 説明 |
|------------------|------|
| `{{topic}}` | 調査クエリ全文（改行を含む場合あり） |
| `{{topic_short}}` | 先頭行・最大 60 文字 — **件名ではこちらを使う** |
| `{{date}}` | `YYYY-MM-DD` |
| `{{scan_date}}` | `YYYY-MM-DD HH:MM UTC` |
| `{{new_items}}` | 前回以降の新着（HTML） |
| `{{all_items}}` | 今回の全件（HTML） |

Resend は件名の改行を拒否します。`subject_template` では `{{topic}}` ではなく `{{topic_short}}` を使ってください。

---

## 既存ジョブの更新

ジョブ定義は GitHub Secrets（`JOB_{ID8}_DEF`）にあります。非機密メタ（サイト・スケジュール・テンプレート。**メールアドレスなし**）は `.github/job-meta/{id8}.json` にも保存されます。

UI から再登録せずサイトやテンプレートを変える手順:

1. `scripts/update_helicopter_job_sites.py` をテンプレートとしてコピー
2. `JOB_ID`・`QUERY`・`SITES` を設定
3. `.env` の `JOB_UPDATE_EMAIL` に通知先を設定（未設定時はスクリプト内のデフォルト）
4. リポジトリルートで実行:

```bash
python scripts/update_your_job_sites.py
```

`github_service.update_job()` が Secrets・ワークフロー YAML・job-meta を一括更新します。

---

## job-meta ファイル

| 場所 | 内容 |
|------|------|
| `JOB_{ID8}_DEF`（Secret） | メールアドレスを含むジョブ JSON 全文 |
| `.github/job-meta/{id8}.json`（git） | クエリ・サイト・スケジュール・テンプレート（**メールなし**） |

古いジョブで job-meta が無くても、Secrets だけでスケジューラは動作します。API または更新スクリプトで再保存すると job-meta が作られます。

---

## ログで見るべきメッセージ

| ログ | 意味 |
|------|------|
| `抽出モード: Gemini LLM` | 通常の LLM 抽出 |
| `GEMINI_API_KEY 未設定` | キーワードマッチにフォールバック（精度低下） |
| `一部サイトの分析に失敗` | 部分失敗 — メールの警告を確認 |
| `抽出結果が0件` | 抽出 0 件 — URL とテーマの適合を確認 |
| `JOB_STATE_JSON` が空 | 状態 Secret 未設定 — 初回は空の履歴から開始 |
