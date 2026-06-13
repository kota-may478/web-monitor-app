"""LLMエージェントエンドポイント"""

import logging

from fastapi import APIRouter, HTTPException

from models.schemas import AgentResponse, JobRequest, TestScrapeRequest, TestScrapeResponse
from services import gemini_agent, scraper

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/propose", response_model=AgentResponse)
async def propose(request: JobRequest) -> AgentResponse:
    """LLMに監視サイト候補とメールフォーマットを提案させる"""
    try:
        return await gemini_agent.analyze_and_propose(
            query=request.query,
            schedule_label=request.schedule_label,
            email=request.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception("LLM呼び出しエラー: %s", e)
        raise HTTPException(status_code=500, detail=f"LLM呼び出しに失敗しました: {e}") from e


@router.post("/test-scrape", response_model=TestScrapeResponse)
async def test_scrape(request: TestScrapeRequest) -> TestScrapeResponse:
    """サイト提案確認用のスクレイピングプレビュー"""
    results = await scraper.scrape_site(
        url=request.url,
        keywords=request.keywords,
        css_selector=request.css_selector,
    )
    preview = results[:5]
    return TestScrapeResponse(results=preview, count=len(preview))
