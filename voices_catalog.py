"""HYRON: cached catalog of available Edge TTS voices."""
import asyncio
import logging
import time

import edge_tts
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["voices"])
_logger = logging.getLogger(__name__)
_cache = None
_expires_at = 0.0
_lock = asyncio.Lock()
CACHE_SECONDS = 3600


@router.get("/v1/voices")
async def list_available_voices():
    global _cache, _expires_at
    now = time.monotonic()
    if _cache is not None and now < _expires_at:
        return {"voices": _cache, "count": len(_cache), "cached": True}

    async with _lock:
        now = time.monotonic()
        if _cache is not None and now < _expires_at:
            return {"voices": _cache, "count": len(_cache), "cached": True}
        try:
            raw_voices = await asyncio.wait_for(edge_tts.list_voices(), timeout=25)
            voices = [
                {
                    "id": v["ShortName"],
                    "name": v.get("FriendlyName") or v["ShortName"],
                    "locale": v.get("Locale"),
                    "gender": v.get("Gender"),
                }
                for v in raw_voices
                if v.get("ShortName")
            ]
            voices.sort(key=lambda v: ((v["locale"] or ""), v["name"]))
            _cache = voices
            _expires_at = time.monotonic() + CACHE_SECONDS
            return {"voices": _cache, "count": len(_cache), "cached": False}
        except Exception:
            _logger.exception("Unable to refresh Edge TTS voice catalog")
            if _cache is not None:
                return {"voices": _cache, "count": len(_cache), "cached": True, "stale": True}
            raise HTTPException(status_code=503, detail="Voice catalog temporarily unavailable")
