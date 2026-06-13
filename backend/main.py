"""
FastAPI アプリケーションのエントリーポイント。

設定:
- python-dotenv で .env を読み込む（開発時用）
- CORSMiddleware で FRONTEND_URL（環境変数）からのリクエストを許可
- /api/agent と /api/jobs のルーターを登録
- GET / → ヘルスチェック
- lifespan イベントでGitHub接続確認
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import agent, jobs
from services import github_service

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """起動時にGitHub接続を確認する"""
    try:
        github_service.get_repo()
        logger.info("GitHub接続確認: OK")
    except Exception as e:
        logger.warning("GitHub接続確認: 失敗（%s）— 起動は継続します", e)
    yield


app = FastAPI(title="Web Monitor API", version="1.0.0", lifespan=lifespan)

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent.router)
app.include_router(jobs.router)


@app.get("/")
async def health_check() -> dict:
    """ヘルスチェック"""
    return {"status": "ok", "version": "1.0.0"}
