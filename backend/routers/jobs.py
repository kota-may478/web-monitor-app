"""ジョブ管理エンドポイント"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from models.schemas import ConfirmJobRequest, JobDefinition, JobDetail, JobSummary, UpdateJobRequest
from services import github_service
from services.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"], dependencies=[Depends(verify_api_key)])


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


@router.get("/{job_id}", response_model=JobDetail)
async def get_job(job_id: str) -> JobDetail:
    """ジョブ詳細を取得する（編集フォーム向け）"""
    try:
        repo = github_service.get_repo()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    meta = github_service.get_job_meta(repo, job_id)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail="ジョブのメタファイルが存在しません。このジョブは旧形式で登録されています。削除して再登録してください。",
        )
    try:
        return JobDetail(**meta, email_hidden=True)
    except Exception as e:
        logger.exception("ジョブ詳細の構築に失敗: %s", e)
        raise HTTPException(status_code=500, detail="ジョブ詳細の取得に失敗しました") from e


@router.put("/{job_id}")
async def update_job(job_id: str, request: UpdateJobRequest) -> dict:
    """ジョブを更新する（Secret・メタファイル・ワークフロー）"""
    try:
        repo = github_service.get_repo()
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    meta = github_service.get_job_meta(repo, job_id)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail="ジョブのメタファイルが存在しません。旧形式のジョブは編集できません。削除して再登録してください。",
        )

    created_at = meta.get("created_at") or datetime.now(timezone.utc).isoformat()
    job = JobDefinition(
        id=job_id,
        query=request.query,
        email=request.email,
        schedule_cron=request.schedule_cron,
        schedule_label=request.schedule_label,
        sites=request.sites,
        email_format=request.email_format,
        created_at=created_at,
        active=request.active,
    )

    try:
        if not github_service.update_job(job):
            raise HTTPException(status_code=500, detail="ジョブ更新に失敗しました")
        return {"success": True, "job_id": job.id, "id8": job.id[:8].upper()}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("ジョブ更新エラー: %s", e)
        raise HTTPException(status_code=500, detail=f"ジョブ更新に失敗しました: {e}") from e


@router.delete("/{job_id}")
async def delete_job(job_id: str) -> dict:
    """ジョブを削除する"""
    success = github_service.delete_job(job_id)
    return {"success": success}
