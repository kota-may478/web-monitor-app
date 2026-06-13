"""GitHub API（Secrets・ワークフロー管理）"""

import base64
import json
import logging
import os
import re

from github import Github
from github.GithubException import GithubException
from github.Repository import Repository

from models.schemas import JobDefinition, JobSummary, ScanState

logger = logging.getLogger(__name__)

# ジョブあたり2個 + システム用5個を除いた上限
MAX_JOBS = 48
WORKFLOW_NAME_PREFIX = "Monitor|"


def _secret_name_def(job_id: str) -> str:
    """例: 'abc12345-...' → 'JOB_ABC12345_DEF'"""
    return f"JOB_{job_id[:8].upper()}_DEF"


def _secret_name_state(job_id: str) -> str:
    """例: 'abc12345-...' → 'JOB_ABC12345_STATE'"""
    return f"JOB_{job_id[:8].upper()}_STATE"


def _workflow_path(job_id: str) -> str:
    """ワークフローファイルのパスを返す"""
    id8 = job_id[:8].lower()
    return f".github/workflows/job_{id8}.yml"


def get_repo() -> Repository:
    """
    環境変数 GITHUB_TOKEN, GITHUB_REPO からリポジトリオブジェクトを返す。
    接続失敗時は RuntimeError を raise する。
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("GITHUB_REPO")
    if not token or not repo_name:
        raise RuntimeError("GITHUB_TOKEN または GITHUB_REPO が設定されていません")
    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        return repo
    except GithubException as e:
        raise RuntimeError(f"GitHub接続に失敗しました: {e}") from e


def count_jobs(repo: Repository | None = None) -> int:
    """JOB_*_DEF パターンのSecret数を返す"""
    if repo is None:
        repo = get_repo()
    count = 0
    secrets = repo.get_secrets()
    for secret in secrets:
        if re.match(r"^JOB_[A-F0-9]{8}_DEF$", secret.name):
            count += 1
    return count


def save_job(job: JobDefinition) -> bool:
    """
    ジョブ定義をGitHub Secretsに保存する。
    1. JOB_{ID8}_DEF に JobDefinition の JSON文字列を保存
    2. JOB_{ID8}_STATE に初期ScanState を保存
    成功時 True、失敗時 False を返す。
    """
    try:
        repo = get_repo()
        if count_jobs(repo) >= MAX_JOBS:
            logger.error("ジョブ登録数の上限（%d件）に達しました", MAX_JOBS)
            return False

        job_json = job.model_dump_json()
        initial_state = ScanState().model_dump_json()

        repo.create_secret(_secret_name_def(job.id), job_json)
        repo.create_secret(_secret_name_state(job.id), initial_state)
        return True
    except GithubException as e:
        logger.exception("ジョブSecretの保存に失敗: %s", e)
        return False
    except Exception as e:
        logger.exception("ジョブSecretの保存中に予期しないエラー: %s", e)
        return False


def get_job(job_id: str) -> JobDefinition | None:
    """
    GitHub SecretからJobDefinitionを取得して返す。

    注意: GitHub APIはSecretの値を読み取る直接的なエンドポイントを持たない。
    そのためget_job()はGitHub Actions実行環境（環境変数）からのみ使用可能。
    バックエンドAPIからの呼び出しではジョブ一覧取得にlist_jobs()を使用すること。
    この関数はscheduler/からの呼び出し専用である。
    """
    job_def_json = os.environ.get("JOB_DEF_JSON")
    if not job_def_json:
        return None
    try:
        data = json.loads(job_def_json)
        if data.get("id") != job_id:
            return None
        return JobDefinition.model_validate(data)
    except (json.JSONDecodeError, ValueError) as e:
        logger.exception("ジョブ定義のパースに失敗: %s", e)
        return None


def _parse_workflow_name(name: str) -> dict | None:
    """
    ワークフローnameフィールドをパースする。
    形式: "Monitor|{query[:30]}|{site_count}sites|{schedule_label}|{created_at}"
    """
    if not name.startswith(WORKFLOW_NAME_PREFIX):
        return None
    parts = name.split("|")
    if len(parts) != 5:
        return None
    site_match = re.match(r"^(\d+)sites$", parts[2])
    if not site_match:
        return None
    return {
        "query": parts[1],
        "site_count": int(site_match.group(1)),
        "schedule_label": parts[3],
        "created_at": parts[4],
    }


def list_jobs() -> list[JobSummary]:
    """
    ワークフローYAMLファイルの一覧からジョブ情報を返す。
    GitHub APIはSecret値を返せないため、ワークフローYAMLのnameフィールドから情報を取得する。
    """
    jobs: list[JobSummary] = []
    try:
        repo = get_repo()
        contents = repo.get_contents(".github/workflows")
        if not isinstance(contents, list):
            contents = [contents]

        for item in contents:
            if not item.path.startswith(".github/workflows/job_") or not item.path.endswith(".yml"):
                continue
            id8_match = re.match(r"\.github/workflows/job_([a-f0-9]{8})\.yml$", item.path)
            if not id8_match:
                continue
            id8 = id8_match.group(1).upper()

            try:
                file_content = repo.get_contents(item.path)
                if isinstance(file_content, list):
                    continue
                content = base64.b64decode(file_content.content).decode("utf-8")
            except GithubException:
                continue

            name_match = re.search(r'^name:\s*["\']?(.+?)["\']?\s*$', content, re.MULTILINE)
            if not name_match:
                continue
            parsed = _parse_workflow_name(name_match.group(1).strip())
            if not parsed:
                continue

            # ワークフローからJOB_IDを取得
            job_id_match = re.search(
                r'JOB_ID:\s*["\']?([0-9a-f-]{36})["\']?', content, re.IGNORECASE
            )
            job_id = job_id_match.group(1) if job_id_match else f"{id8.lower()}-0000-0000-0000-000000000000"

            jobs.append(
                JobSummary(
                    id=job_id,
                    id8=id8,
                    query=parsed["query"],
                    schedule_label=parsed["schedule_label"],
                    site_count=parsed["site_count"],
                    created_at=parsed["created_at"],
                    active=True,
                )
            )
    except GithubException as e:
        logger.exception("ジョブ一覧の取得に失敗: %s", e)
    except Exception as e:
        logger.exception("ジョブ一覧の取得中に予期しないエラー: %s", e)

    return jobs


def delete_job(job_id: str) -> bool:
    """
    1. JOB_{ID8}_DEF Secretを削除
    2. JOB_{ID8}_STATE Secretを削除
    3. .github/workflows/job_{id8}.yml を削除
    全て成功時 True を返す。
    """
    try:
        repo = get_repo()
        id8 = job_id[:8].lower()

        for secret_name in [_secret_name_def(job_id), _secret_name_state(job_id)]:
            try:
                repo.get_secret(secret_name).delete()
            except GithubException as e:
                if e.status != 404:
                    logger.warning("Secret %s の削除に失敗: %s", secret_name, e)

        workflow_path = _workflow_path(job_id)
        try:
            file_content = repo.get_contents(workflow_path)
            if not isinstance(file_content, list):
                repo.delete_file(
                    workflow_path,
                    f"Delete job workflow {id8}",
                    file_content.sha,
                )
        except GithubException as e:
            if e.status != 404:
                logger.warning("ワークフロー %s の削除に失敗: %s", workflow_path, e)
                return False

        return True
    except Exception as e:
        logger.exception("ジョブ削除中にエラー: %s", e)
        return False


def generate_workflow_yaml(job: JobDefinition) -> str:
    """
    GitHub Actions ワークフローYAMLを文字列で生成して返す。
    """
    id8 = job.id[:8].upper()
    repo_name = os.environ.get("GITHUB_REPO", "owner/repo")
    query_short = job.query[:30]
    workflow_name = (
        f"{WORKFLOW_NAME_PREFIX}{query_short}|{len(job.sites)}sites|"
        f"{job.schedule_label}|{job.created_at}"
    )

    return f"""name: "{workflow_name}"
on:
  schedule:
    - cron: "{job.schedule_cron}"
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    env:
      JOB_ID: "{job.id}"
      JOB_DEF_JSON: ${{{{ secrets.JOB_{id8}_DEF }}}}
      JOB_STATE_JSON: ${{{{ secrets.JOB_{id8}_STATE }}}}
      RESEND_API_KEY: ${{{{ secrets.RESEND_API_KEY }}}}
      RESEND_FROM_EMAIL: ${{{{ secrets.RESEND_FROM_EMAIL }}}}
      GITHUB_TOKEN_FOR_SECRETS: ${{{{ secrets.GITHUB_PAT }}}}
      GITHUB_REPO: "{repo_name}"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r scheduler/requirements.txt
      - name: Run monitor job
        run: python scheduler/run_job.py
"""


def push_workflow(job: JobDefinition) -> bool:
    """
    .github/workflows/job_{id8}.yml をリポジトリにpushする。
    ファイルが既存の場合は update、新規の場合は create する。
    """
    try:
        repo = get_repo()
        workflow_path = _workflow_path(job.id)
        yaml_content = generate_workflow_yaml(job)
        commit_message = f"Add/update monitor workflow for job {job.id[:8]}"

        try:
            existing = repo.get_contents(workflow_path)
            if isinstance(existing, list):
                return False
            repo.update_file(
                workflow_path,
                commit_message,
                yaml_content,
                existing.sha,
            )
        except GithubException as e:
            if e.status == 404:
                repo.create_file(
                    workflow_path,
                    commit_message,
                    yaml_content,
                )
            else:
                raise
        return True
    except Exception as e:
        logger.exception("ワークフローのpushに失敗: %s", e)
        return False
