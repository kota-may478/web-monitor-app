"""API キー認証ユーティリティ

環境変数 API_KEY が設定されている場合、X-Api-Key ヘッダーを検証する。
未設定時（ローカル開発）は認証をスキップする。
"""

import os
from typing import Annotated

from fastapi import Header, HTTPException

_API_KEY = os.environ.get("API_KEY", "")


async def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Dependency: X-Api-Key ヘッダーを検証する"""
    if not _API_KEY:
        return
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="API キーが無効または未指定です")
