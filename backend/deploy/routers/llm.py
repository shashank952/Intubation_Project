import asyncio

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..config import settings
from ..llm_assistant import check_llm_connection

router = APIRouter(prefix="/api/llm", tags=["llm"])

_STATUS_PROBE_TIMEOUT = settings.llm_timeout + 3


@router.get("/status")
async def llm_status(_: dict = Depends(get_current_user)):
    try:
        connected, latency_ms = await asyncio.wait_for(
            asyncio.to_thread(check_llm_connection),
            timeout=_STATUS_PROBE_TIMEOUT,
        )
    except asyncio.TimeoutError:
        connected, latency_ms = False, None
    return {
        "connected": connected,
        "model": settings.llm_model,
        "latency_ms": latency_ms,
    }