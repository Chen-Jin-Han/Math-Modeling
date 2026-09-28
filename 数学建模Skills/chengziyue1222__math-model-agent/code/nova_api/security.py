"""Minimal server-to-server API key authentication."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def require_api_key(x_nova_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("NOVA_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail={"code": "AUTH_NOT_CONFIGURED", "message": "NOVA_API_KEY is not configured."})
    if not x_nova_api_key or not hmac.compare_digest(x_nova_api_key, expected):
        raise HTTPException(status_code=401, detail={"code": "AUTH_FAILED", "message": "Invalid API key."})
