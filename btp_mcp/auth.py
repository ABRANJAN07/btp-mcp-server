"""
auth.py — Fetches and caches an OAuth2 access token from SAP BTP.

Unchanged from Phase 1 in structure — single credential set.

NOTE — Entitlements API skipped for now:
  When entitlements are re-enabled, this file will need a second
  token function (get_cis_token) for the CIS Central credentials.
  That code is commented out at the bottom of this file for reference.

How it works:
  1. We POST to BTP's UAA token endpoint with client_id + client_secret
  2. BTP returns an access_token valid for ~12 hours
  3. We cache it in memory — reuse until 60 seconds before expiry
  4. Every BTP API call passes this token as: Authorization: Bearer <token>
"""

import time
import httpx
from config import settings


# ── In-memory token cache ──────────────────────────────────────────────────
# Simple module-level variables — no external cache needed.
_cached_token: str = ""
_token_expires_at: float = 0.0


async def get_access_token() -> str:
    """
    Returns a valid BTP access token for the Service Manager API.
    Fetches a fresh one only when the cached token has expired.
    """
    global _cached_token, _token_expires_at

    # Return cached token if still valid (with 60s safety buffer)
    if _cached_token and time.time() < (_token_expires_at - 60):
        return _cached_token

    # Fetch a new token
    print("  [auth] Fetching new SM token from BTP...")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            url=settings.btp_token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.btp_client_id,
                "client_secret": settings.btp_client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        raise Exception(
            f"Token fetch failed — HTTP {response.status_code}\n"
            f"Check BTP_CLIENT_ID and BTP_CLIENT_SECRET in your .env\n"
            f"Response: {response.text}"
        )

    data = response.json()
    _cached_token = data["access_token"]
    expires_in = data.get("expires_in", 43200)
    _token_expires_at = time.time() + expires_in

    print(f"  [auth] SM token fetched. Valid for {expires_in // 3600}h")
    return _cached_token


async def get_auth_headers() -> dict:
    """
    Returns the Authorization header for Service Manager API calls.
    Also used for Destination API calls — same token works for both.
    """
    token = await get_access_token()
    return {"Authorization": f"Bearer {token}"}


# ── ENTITLEMENTS — commented out, re-enable when CIS key is ready ──────────
#
# When the CIS Central service key is available, uncomment this section
# and update btp_client.py to call get_cis_headers() for entitlements.
#
# _cis_token: str = ""
# _cis_expires_at: float = 0.0
#
# async def get_cis_token() -> str:
#     """Token for CIS Central / Entitlements API."""
#     global _cis_token, _cis_expires_at
#
#     if _cis_token and time.time() < (_cis_expires_at - 60):
#         return _cis_token
#
#     print("  [auth] Fetching new CIS token from BTP...")
#     async with httpx.AsyncClient(timeout=30) as client:
#         response = await client.post(
#             url=settings.btp_cis_token_url,
#             data={
#                 "grant_type": "client_credentials",
#                 "client_id": settings.btp_cis_client_id,
#                 "client_secret": settings.btp_cis_client_secret,
#             },
#             headers={"Content-Type": "application/x-www-form-urlencoded"},
#         )
#     if response.status_code != 200:
#         raise Exception(f"CIS token fetch failed — HTTP {response.status_code}\n{response.text}")
#     data = response.json()
#     _cis_token = data["access_token"]
#     expires_in = data.get("expires_in", 43200)
#     _cis_expires_at = time.time() + expires_in
#     print(f"  [auth] CIS token fetched. Valid for {expires_in // 3600}h")
#     return _cis_token
#
# async def get_cis_headers() -> dict:
#     """Authorization headers for CIS / Entitlements API calls."""
#     return {"Authorization": f"Bearer {await get_cis_token()}"}
#
# ── end of commented entitlements section ─────────────────────────────────