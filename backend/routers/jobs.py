"""ジョブ管理エンドポイント"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from models.schemas import ConfirmJobRequest, JobDefinition, JobSummary
from services import github_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/confirm")
async def confirm_job(request: ConfirmJobRequest) -> dict:
    """ジョブをGitHub Secretsとワークフローに登録する"""
    job = request.job
    if not job.id:
        job = JobDefinition(
            **{**job.model_dump(), "id": str(uuid.uuid4())}
        )
    if not job.created_at:
        job = JobDefinition(
            **{**job.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()}
        )

    try:
        repo = github_service.get_repo()
        if github_service.count_jobs(repo) >= github_service.MAX_JOBS:
            raise HTTPException(
                status_code=429,
                detail="ジョブ登録数の上限（48件）に達しました",
            )

        if not github_service.save_job(job):
            raise HTTPException(status_code=500, detail="ジョブの保存に失敗しました")

        if not github_service.push_workflow(job):
            raise HTTPException(status_code=500, detail="ワークフローの登録に失敗しました")

        return {
            "success": True,
            "job_id": job.id,
            "id8": job.id[:8].upper(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ジョブ登録エラー: %s", e)
        raise HTTPException(status_code=500, detail=f"ジョブ登録に失敗しました: {e}") from e


@router.get("", response_model=list[JobSummary])
async def list_jobs() -> list[JobSummary]:
    """登録済みジョブ一覧を取得する"""
    return github_service.list_jobs()


@router.delete("/{job_id}")
async def delete_job(job_id: str) -> dict:
    """ジョブを削除する"""
    success = github_service.delete_job(job_id)
    return {"success": success}
