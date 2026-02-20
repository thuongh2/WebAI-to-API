# src/app/endpoints/admin_api.py
import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import CONFIG, write_config
from app.logger import logger
from app.services.gemini_client import (
    GeminiClientNotInitializedError,
    get_client_status,
    get_gemini_client,
    init_gemini_client,
)
from app.services.curl_parser import parse_curl_command
from app.services.log_broadcaster import SSELogBroadcaster
from app.services.stats_collector import StatsCollector

router = APIRouter(prefix="/api/admin", tags=["Admin API"])


# --- Request models ---


class CurlImportRequest(BaseModel):
    curl_text: str


class CookieUpdateRequest(BaseModel):
    secure_1psid: str
    secure_1psidts: str


class ModelUpdateRequest(BaseModel):
    model: str


class ProxyUpdateRequest(BaseModel):
    http_proxy: str


# --- Dashboard ---


@router.get("/status")
async def get_status():
    """Return overall system status for the dashboard."""
    stats = StatsCollector.get_instance().get_stats()
    client_status = get_client_status()

    try:
        get_gemini_client()
        gemini_status = "connected"
    except GeminiClientNotInitializedError:
        gemini_status = "disconnected"

    return {
        "gemini_status": gemini_status,
        "client_error": client_status.get("error"),
        "error_code": client_status.get("error_code"),
        "current_model": CONFIG["AI"].get("default_model_gemini", "unknown"),
        "proxy": CONFIG["Proxy"].get("http_proxy", ""),
        "browser": CONFIG["Browser"].get("name", "unknown"),
        "stats": stats,
    }


# --- Config ---


@router.get("/config")
async def get_config():
    """Return current configuration (masking sensitive cookie values)."""
    return {
        "browser": CONFIG["Browser"].get("name", "chrome"),
        "model": CONFIG["AI"].get("default_model_gemini", "gemini-3.0-pro"),
        "proxy": CONFIG["Proxy"].get("http_proxy", ""),
        "cookies_set": bool(
            CONFIG["Cookies"].get("gemini_cookie_1psid")
            and CONFIG["Cookies"].get("gemini_cookie_1psidts")
        ),
        "cookie_1psid_preview": _mask_value(
            CONFIG["Cookies"].get("gemini_cookie_1psid", "")
        ),
        "cookie_1psidts_preview": _mask_value(
            CONFIG["Cookies"].get("gemini_cookie_1psidts", "")
        ),
        "gemini_enabled": CONFIG.getboolean("EnabledAI", "gemini", fallback=True),
        "available_models": [
            "gemini-3.0-pro",
            "gemini-3.0-flash",
            "gemini-3.0-flash-thinking",
        ],
    }


@router.post("/config/curl-import")
async def import_from_curl(request: CurlImportRequest):
    """Parse a cURL command or cookie string and extract Gemini cookies."""
    result = parse_curl_command(request.curl_text)
    if not result.is_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Could not extract required cookies",
                "errors": result.errors,
                "found_cookies": list(result.all_cookies.keys()),
            },
        )
    CONFIG["Cookies"]["gemini_cookie_1psid"] = result.secure_1psid
    CONFIG["Cookies"]["gemini_cookie_1psidts"] = result.secure_1psidts
    write_config(CONFIG)
    logger.info("Cookies imported from cURL, reinitializing client...")
    success = await init_gemini_client()
    status = get_client_status()
    return {
        "success": success,
        "cookies_saved": True,
        "message": (
            "Cookies imported and client connected successfully!"
            if success
            else "Cookies saved but connection failed"
        ),
        "error_code": status.get("error_code"),
        "error_detail": status.get("error"),
        "url_detected": result.url,
    }


@router.post("/config/cookies")
async def update_cookies(request: CookieUpdateRequest):
    """Update cookie values and reinitialize the Gemini client."""
    CONFIG["Cookies"]["gemini_cookie_1psid"] = request.secure_1psid
    CONFIG["Cookies"]["gemini_cookie_1psidts"] = request.secure_1psidts
    write_config(CONFIG)
    logger.info("Cookies updated via admin UI, reinitializing client...")
    success = await init_gemini_client()
    status = get_client_status()
    return {
        "success": success,
        "cookies_saved": True,
        "message": "Client connected successfully!" if success else "Cookies saved but connection failed",
        "error_code": status.get("error_code"),
        "error_detail": status.get("error"),
    }


@router.post("/config/model")
async def update_model(request: ModelUpdateRequest):
    """Update the default Gemini model."""
    CONFIG["AI"]["default_model_gemini"] = request.model
    write_config(CONFIG)
    return {"success": True, "model": request.model}


@router.post("/config/proxy")
async def update_proxy(request: ProxyUpdateRequest):
    """Update proxy settings and reinitialize client."""
    CONFIG["Proxy"]["http_proxy"] = request.http_proxy
    write_config(CONFIG)
    logger.info("Proxy updated, reinitializing client...")
    success = await init_gemini_client()
    return {"success": success}


@router.post("/client/reinitialize")
async def reinitialize_client():
    """Force reinitialize the Gemini client with current config."""
    success = await init_gemini_client()
    status = get_client_status()
    return {
        "success": success,
        "message": "Client connected successfully!" if success else "Connection failed",
        "error_code": status.get("error_code"),
        "error_detail": status.get("error"),
    }


# --- SSE Logs ---


@router.get("/logs/stream")
async def stream_logs(request: Request, last_id: int = 0):
    """SSE endpoint for real-time log streaming."""
    broadcaster = SSELogBroadcaster.get_instance()

    async def event_generator():
        async for entry in broadcaster.subscribe(last_id):
            if await request.is_disconnected():
                break
            yield {
                "event": "log",
                "id": str(entry["id"]),
                "data": json.dumps(entry),
            }

    return EventSourceResponse(event_generator())


@router.get("/logs/recent")
async def get_recent_logs(count: int = 50):
    """Return recent log entries for initial page load."""
    broadcaster = SSELogBroadcaster.get_instance()
    return {"logs": broadcaster.get_recent(count)}


# --- Helpers ---


def _mask_value(value: str) -> str:
    """Show first 8 and last 4 chars, mask the rest."""
    if not value or len(value) < 16:
        return "***" if value else ""
    return f"{value[:8]}...{value[-4:]}"
