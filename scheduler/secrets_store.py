"""
GitHub SecretsのAPIラッパー。
scheduler/の各スクリプトから共通で使用する。

GitHub Actions実行環境では以下の環境変数が利用可能:
  GITHUB_TOKEN_FOR_SECRETS : Personal Access Token（Secrets読み書き用）
  GITHUB_REPO              : リポジトリ名（owner/repo）
  JOB_ID                   : 実行対象のジョブID

注意: GitHub APIはSecretの値をGETでは返さない。
Secretの値はGitHub Actions実行時に環境変数として注入されるため、
scheduler/run_job.py では os.environ から直接読み取る。
"""

import json
import logging
import os

from github import Github
from github.GithubException import GithubException

logger = logging.getLogger(__name__)


def _secret_name_state(job_id: str) -> str:
    """例: 'abc12345-...' → 'JOB_ABC12345_STATE'"""
    return f"JOB_{job_id[:8].upper()}_STATE"


def get_job_def() -> dict:
    """
    環境変数 JOB_DEF_JSON からジョブ定義を読み取る。
    GitHub Actionsのワークフローで環境変数として注入される。
    """
    job_def_json = os.environ.get("JOB_DEF_JSON", "")
    if not job_def_json:
        raise ValueError("JOB_DEF_JSON 環境変数が設定されていません")
    return json.loads(job_def_json)


def get_job_state() -> dict:
    """
    環境変数 JOB_STATE_JSON からスキャン状態を読み取る。
    初回実行時（環境変数が空）は {"last_scan": null, "items": []} を返す。
    """
    state_json = os.environ.get("JOB_STATE_JSON", "")
    if not state_json:
        return {"last_scan": None, "items": []}
    try:
        return json.loads(state_json)
    except json.JSONDecodeError:
        logger.warning("JOB_STATE_JSON のパースに失敗、初期状態を使用")
        return {"last_scan": None, "items": []}


def save_job_state(job_id: str, state: dict) -> bool:
    """
    GitHub API経由でJOB_{ID8}_STATE Secretを更新する。
    環境変数 GITHUB_TOKEN_FOR_SECRETS, GITHUB_REPO を使用する。
    state["items"] は最大50件に切り詰める。
    """
    token = os.environ.get("GITHUB_TOKEN_FOR_SECRETS")
    repo_name = os.environ.get("GITHUB_REPO")
    if not token or not repo_name:
        logger.error("GITHUB_TOKEN_FOR_SECRETS または GITHUB_REPO が未設定")
        return False

    items = state.get("items", [])
    if len(items) > 50:
        state["items"] = items[:50]

    try:
        gh = Github(token)
        repo = gh.get_repo(repo_name)
        secret_name = _secret_name_state(job_id)
        repo.create_secret(secret_name, json.dumps(state, ensure_ascii=False))
        return True
    except GithubException as e:
        logger.exception("状態Secretの更新に失敗: %s", e)
        return False
    except Exception as e:
        logger.exception("状態Secretの更新中に予期しないエラー: %s", e)
        return False
