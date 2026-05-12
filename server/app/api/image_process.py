"""图片处理 API（抠图去背景等）"""
import io
import asyncio
import logging
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# rembg session 缓存（避免每次请求重新加载模型）
_rembg_session = None


def _get_rembg_session():
    """懒加载 rembg session（首次调用时加载模型，后续复用）"""
    global _rembg_session
    if _rembg_session is None:
        from rembg import new_session
        logger.info("Loading rembg model (first call, may take a while)...")
        _rembg_session = new_session("u2net")
        logger.info("rembg model loaded successfully")
    return _rembg_session


class RemoveBgRequest(BaseModel):
    image_url: str


@router.post("/remove-bg")
async def remove_bg(body: RemoveBgRequest):
    """接收图片 URL，返回去除背景后的 PNG 图片"""
    # 1. 下载图片
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(body.image_url)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"下载图片失败 (HTTP {resp.status_code})")
            image_data = resp.content
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"下载图片失败: {str(e)}")

    if len(image_data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片太大，最大支持 20MB")

    # 2. 在线程池中执行抠图（避免阻塞事件循环）
    try:
        session = _get_rembg_session()
        loop = asyncio.get_event_loop()
        output_data = await loop.run_in_executor(
            None,
            _remove_bg_sync,
            image_data,
            session,
        )
    except Exception as e:
        logger.error(f"Background removal failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"抠图处理失败: {str(e)}")

    # 3. 返回 PNG 图片
    return Response(content=output_data, media_type="image/png")


def _remove_bg_sync(image_data: bytes, session) -> bytes:
    """同步执行抠图（在线程池中运行）"""
    from rembg import remove
    return remove(image_data, session=session)
