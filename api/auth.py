# -*- coding: utf-8 -*-
"""
API Authentication module for futures_v6.

Supports:
  - API Key via X-API-Key header
  - JWT Token via Authorization: Bearer header
  - Role-based access: admin (all) / read_only (GET only)

Whitelisted endpoints (no auth required):
  - GET /health
  - GET /
  - GET /docs, /openapi.json
  - GET /assets/* (frontend static)

@date 2026-05-07
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("auth")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_API_KEYS_PATH = Path(__file__).parent.parent / "config" / "api_keys.json"
_JWT_SECRET = os.environ.get("JWT_SECRET", "futures_v6_dev_secret_change_in_prod")
_JWT_EXPIRY_SECONDS = 86400  # 24 hours

# Whitelist: paths that don't need auth
_AUTH_WHITELIST = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",  # login endpoint is public
}

# Prefixes that bypass auth
_AUTH_WHITELIST_PREFIXES = (
    "/assets/",  # frontend static files
)

# ---------------------------------------------------------------------------
# API Key store
# ---------------------------------------------------------------------------

_api_key_store: dict[str, dict] = {}  # key -> {"name": str, "role": str}


def _load_api_keys() -> None:
    """Load API keys from config file."""
    global _api_key_store
    try:
        if _API_KEYS_PATH.exists():
            with open(_API_KEYS_PATH, "r", encoding="utf-8") as f:
                keys_list = json.load(f)
            _api_key_store = {k["key"]: k for k in keys_list if "key" in k and "role" in k}
            logger.info("Loaded %d API keys from %s", len(_api_key_store), _API_KEYS_PATH)
        else:
            logger.warning("API keys file not found: %s (auth disabled)", _API_KEYS_PATH)
    except Exception as e:
        logger.error("Failed to load API keys: %s", e)


def get_key_info(api_key: str) -> Optional[dict]:
    """Look up API key. Returns {"name", "role"} or None."""
    return _api_key_store.get(api_key)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _create_jwt(payload: dict) -> str:
    """Create a JWT token. Uses PyJWT if available, else HMAC fallback."""
    try:
        import jwt
        return jwt.encode(payload, _JWT_SECRET, algorithm="HS256")
    except ImportError:
        # Fallback: simple HMAC-based token
        import hashlib
        import base64
        import json as _json
        header = base64.urlsafe_b64encode(_json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        body = base64.urlsafe_b64encode(_json.dumps(payload).encode()).decode().rstrip("=")
        sig_input = f"{header}.{body}".encode()
        sig = base64.urlsafe_b64encode(
            hashlib.sha256(sig_input + _JWT_SECRET.encode()).digest()
        ).decode().rstrip("=")
        return f"{header}.{body}.{sig}"


def _decode_jwt(token: str) -> Optional[dict]:
    """Decode a JWT token. Returns payload or None."""
    try:
        import jwt
        payload = jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        return payload
    except ImportError:
        # Fallback: verify HMAC
        import hashlib
        import base64
        import json as _json
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b, body_b, sig_b = parts
        sig_input = f"{header_b}.{body_b}".encode()
        expected_sig = base64.urlsafe_b64encode(
            hashlib.sha256(sig_input + _JWT_SECRET.encode()).digest()
        ).decode().rstrip("=")
        if sig_b != expected_sig:
            return None
        try:
            padding = 4 - len(body_b) % 4
            if padding != 4:
                body_b += "=" * padding
            payload = _json.loads(base64.urlsafe_b64decode(body_b))
            return payload
        except Exception:
            return None
    except Exception:
        return None


def create_token(key_name: str, role: str) -> str:
    """Create a JWT token for the given key."""
    now = int(time.time())
    payload = {
        "sub": key_name,
        "role": role,
        "iat": now,
        "exp": now + _JWT_EXPIRY_SECONDS,
    }
    return _create_jwt(payload)


# ---------------------------------------------------------------------------
# Auth middleware for FastAPI
# ---------------------------------------------------------------------------

def create_auth_middleware(app):
    """Register HTTP middleware for API authentication."""
    from starlette.requests import Request
    from starlette.responses import JSONResponse

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # 1. Check whitelist
        path = request.url.path
        if path in _AUTH_WHITELIST:
            return await call_next(request)
        if path.startswith(_AUTH_WHITELIST_PREFIXES):
            return await call_next(request)
        # Root path
        if path == "/":
            return await call_next(request)

        # 2. If no API keys loaded, skip auth (development mode)
        if not _api_key_store:
            return await call_next(request)

        # 3. Extract credentials
        role = None
        key_name = None

        # Try API Key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            info = get_key_info(api_key)
            if info:
                role = info["role"]
                key_name = info["name"]
            else:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key"}
                )
        else:
            # Try JWT Bearer token
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = _decode_jwt(token)
                if payload is None:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid or expired token"}
                    )
                # Check expiry
                if "exp" in payload and payload["exp"] < time.time():
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Token expired"}
                    )
                role = payload.get("role")
                key_name = payload.get("sub")
            else:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing authentication: provide X-API-Key header or Authorization: Bearer token"}
                )

        # 4. Role check: read_only can only do GET
        if role == "read_only" and request.method not in ("GET", "HEAD", "OPTIONS"):
            return JSONResponse(
                status_code=403,
                content={"detail": f"read_only role cannot perform {request.method} requests"}
            )

        # 5. Attach user info to request state
        request.state.user = key_name
        request.state.user_role = role

        return await call_next(request)

    return app


# ---------------------------------------------------------------------------
# Login endpoint helper
# ---------------------------------------------------------------------------

def handle_login(api_key: str) -> dict:
    """
    Validate API key and return JWT token.
    Returns {"token": "...", "role": "...", "name": "..."} on success,
    or raises ValueError on failure.
    """
    info = get_key_info(api_key)
    if not info:
        raise ValueError("Invalid API key")

    token = create_token(info["name"], info["role"])
    return {
        "token": token,
        "role": info["role"],
        "name": info["name"],
    }


# Initialize on import
_load_api_keys()
