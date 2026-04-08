"""
auth.py — Fetches an OAuth2 access token from SAP BTP.

BTP uses the "client_credentials" grant type.
This means: we send our client_id + client_secret,
and BTP gives us back a temporary access token (~12 hours).

We cache the token in memory so we don't fetch a new one
on every single API call — we reuse it until it expires.
"""

import time
import httpx
from .config import settings   # our settings from .env


# Simple in-memory cache — just two variables
_cached_token: str = ""
_token_expires_at: float = 0.0


async def get_access_token() -> str:
    """
    Returns a valid BTP access token.
    Fetches a new one from BTP if the cached one has expired.
    """
    global _cached_token, _token_expires_at

    # Check if we still have a valid token
    # We subtract 60 seconds as a safety buffer before expiry
    if _cached_token and time.time() < (_token_expires_at - 60):
        print("  [auth] Using cached token")
        return _cached_token

    # Token is missing or expired — fetch a new one
    print("  [auth] Fetching new token from BTP...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=settings.btp_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.btp_client_id,
                "client_secret": settings.btp_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30,
        )

    # If BTP returns an error, raise it clearly
    if response.status_code != 200:
        raise Exception(
            f"Token fetch failed. Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    data = response.json()
    # print(f"Response from BTP token endpoint: {data}")

    # Store the token and calculate when it expires
    _cached_token = data["access_token"]
    expires_in = data.get("expires_in", 43200)   # default 12 hours
    _token_expires_at = time.time() + expires_in

    print(f"  [auth] New token fetched. Expires in {expires_in // 3600}h")
    return _cached_token


async def get_auth_headers() -> dict:
    """
    Returns the Authorization header needed for BTP API calls.
    All BTP APIs expect: Authorization: Bearer <token>
    """
    token = await get_access_token()
    return {"Authorization": f"Bearer {token}"}