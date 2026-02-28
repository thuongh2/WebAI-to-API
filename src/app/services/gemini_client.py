# src/app/services/gemini_client.py
import asyncio
import os
from models.gemini import MyGeminiClient
from app.config import CONFIG, write_config
from app.logger import logger
from app.utils.browser import get_cookie_from_browser

# Import the specific exception to handle it gracefully
from gemini_webapi.exceptions import AuthError


class GeminiClientNotInitializedError(Exception):
    """Raised when the Gemini client is not initialized or initialization failed."""
    pass


# Global variable to store the Gemini client instance
_gemini_client = None
_initialization_error = None
_error_code = None  # "auth_expired", "no_cookies", "network", "disabled", "unknown"
_persist_task: asyncio.Task = None  # Background task for persisting rotated cookies


def _normalize_cookie(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().strip('"').strip("'")


def _env_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


async def init_gemini_client() -> bool:
    """
    Initialize and set up the Gemini client based on the configuration.
    Returns True on success, False on failure.
    """
    global _gemini_client, _initialization_error, _error_code
    _initialization_error = None
    _error_code = None

    if CONFIG.getboolean("EnabledAI", "gemini", fallback=True):
        gemini_proxy = CONFIG["Proxy"].get("http_proxy")
        if gemini_proxy == "":
            gemini_proxy = None

        env_1psid = _normalize_cookie(os.environ.get("GEMINI_COOKIE_1PSID"))
        env_1psidts = _normalize_cookie(os.environ.get("GEMINI_COOKIE_1PSIDTS"))
        cfg_1psid = _normalize_cookie(CONFIG["Cookies"].get("gemini_cookie_1PSID"))
        cfg_1psidts = _normalize_cookie(CONFIG["Cookies"].get("gemini_cookie_1PSIDTS"))

        candidates: list[tuple[str, str, str]] = []
        if env_1psid and env_1psidts:
            candidates.append(("env", env_1psid, env_1psidts))
        if cfg_1psid and cfg_1psidts and (cfg_1psid, cfg_1psidts) != (env_1psid, env_1psidts):
            candidates.append(("config", cfg_1psid, cfg_1psidts))

        disable_browser_fallback = _env_truthy(os.environ.get("DISABLE_BROWSER_COOKIE_FALLBACK"))
        if not candidates and not disable_browser_fallback:
            cookies = get_cookie_from_browser("gemini")
            if cookies:
                browser_1psid, browser_1psidts = _normalize_cookie(cookies[0]), _normalize_cookie(cookies[1])
                if browser_1psid and browser_1psidts:
                    candidates.append(("browser", browser_1psid, browser_1psidts))

        if not candidates:
            _error_code = "no_cookies"
            _initialization_error = (
                "Gemini cookies not found. Provide GEMINI_COOKIE_1PSID and GEMINI_COOKIE_1PSIDTS "
                "or set them in config."
            )
            logger.error(_initialization_error)
            return False

        last_auth_error = None
        for source, gemini_cookie_1PSID, gemini_cookie_1PSIDTS in candidates:
            try:
                _gemini_client = MyGeminiClient(
                    secure_1psid=gemini_cookie_1PSID,
                    secure_1psidts=gemini_cookie_1PSIDTS,
                    proxy=gemini_proxy,
                )
                await _gemini_client.init()
                logger.info(f"Gemini client initialized successfully using {source} cookies.")
                return True
            except AuthError as e:
                last_auth_error = e
                _gemini_client = None
                logger.warning(f"Gemini auth failed using {source} cookies: {e}")
            except (ConnectionError, OSError, TimeoutError) as e:
                _error_code = "network"
                _initialization_error = str(e)
                logger.error(f"Network error initializing Gemini client: {e}")
                _gemini_client = None
                return False
            except Exception as e:
                _error_code = "unknown"
                _initialization_error = str(e)
                logger.error(f"Unexpected error initializing Gemini client: {e}", exc_info=True)
                _gemini_client = None
                return False

        _error_code = "auth_expired"
        _initialization_error = str(last_auth_error) if last_auth_error else "Gemini authentication failed."
        logger.error(f"Gemini authentication failed: {_initialization_error}")
        return False
    else:
        _error_code = "disabled"
        _initialization_error = "Gemini client is disabled in config."
        logger.info(_initialization_error)
        return False


def get_gemini_client():
    """
    Returns the initialized Gemini client instance.

    Raises:
        GeminiClientNotInitializedError: If the client is not initialized.
    """
    if _gemini_client is None:
        error_detail = _initialization_error or "Gemini client was not initialized. Check logs for details."
        raise GeminiClientNotInitializedError(error_detail)
    return _gemini_client


def get_client_status() -> dict:
    """Return the current status of the Gemini client for the admin UI."""
    return {
        "initialized": _gemini_client is not None,
        "error": _initialization_error,
        "error_code": _error_code,
    }


async def _persist_cookies_loop():
    """
    Background task that watches for cookie rotation by gemini-webapi's auto_refresh
    mechanism and persists any updated values back to config.conf.

    The library rotates __Secure-1PSIDTS every ~9 minutes in-memory only.
    Without this task, a server restart would reload the original (expired) cookies.
    """
    # Wait one full refresh cycle before first check so the library has time to rotate
    await asyncio.sleep(600)
    while True:
        try:
            if _gemini_client is not None:
                # Access the underlying WebGeminiClient cookies dict
                client_cookies = _gemini_client.client.cookies
                new_1psid = client_cookies.get("__Secure-1PSID")
                new_1psidts = client_cookies.get("__Secure-1PSIDTS")

                current_1psid = CONFIG["Cookies"].get("gemini_cookie_1PSID", "")
                current_1psidts = CONFIG["Cookies"].get("gemini_cookie_1PSIDTS", "")

                changed = False
                if new_1psid and new_1psid != current_1psid:
                    CONFIG["Cookies"]["gemini_cookie_1PSID"] = new_1psid
                    changed = True
                    logger.info("__Secure-1PSID rotated — will persist to config.")
                if new_1psidts and new_1psidts != current_1psidts:
                    CONFIG["Cookies"]["gemini_cookie_1PSIDTS"] = new_1psidts
                    changed = True
                    logger.info("__Secure-1PSIDTS rotated — will persist to config.")

                if changed:
                    write_config(CONFIG)
                    logger.info("Rotated Gemini cookies persisted to config.conf.")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Cookie persist check failed: {e}")

        await asyncio.sleep(600)  # Re-check every 10 minutes


def start_cookie_persister() -> asyncio.Task:
    """Start the background cookie-persist task. Safe to call multiple times."""
    global _persist_task
    if _persist_task is not None and not _persist_task.done():
        return _persist_task
    _persist_task = asyncio.create_task(_persist_cookies_loop())
    logger.info("Cookie persist task started (checks every 10 min).")
    return _persist_task


def stop_cookie_persister():
    """Cancel the cookie persister task on shutdown."""
    global _persist_task
    if _persist_task is not None and not _persist_task.done():
        _persist_task.cancel()
        logger.info("Cookie persist task stopped.")
    _persist_task = None
