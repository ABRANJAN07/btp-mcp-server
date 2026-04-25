"""
btp_client.py — Calls BTP APIs and returns typed Pydantic models.

Active APIs (3):
  1. Service Manager — service offerings (catalog)
  2. Service Manager — service plans
  3. Service Manager — service instances
  4. Destination Service — configured connections

NOTE — Entitlements API commented out:
  The get_entitlements() function is preserved below but commented out.
  It requires a separate CIS Central service key to work.
  Re-enable it when that key is available.

Each active function follows the same pattern:
  1. Check TTL cache — return immediately if fresh data exists
  2. Call BTP API (with pagination for list endpoints)
  3. Parse raw JSON → typed Pydantic models
  4. Store in cache and return
"""

import httpx
from btp_mcp.auth import get_auth_headers
from btp_mcp.cache import get_cached, set_cached
from btp_mcp.config import settings
from btp_mcp.models import (
    Destination,
    ServiceInstance,
    ServiceOffering,
    ServicePlan,
    # EntitlementItem,  # commented out — re-enable with CIS key
)


# ── Helper: fetch all pages from a BTP list endpoint ──────────────────────

async def _get_all_pages(base_url: str, params: dict | None = None) -> list[dict]:
    """
    Fetches ALL pages from a BTP API endpoint.

    BTP returns up to 50 items per page with a "token" field
    for the next page. This helper loops until all items are collected.

    Args:
        base_url: The API endpoint URL
        params:   Optional extra query parameters

    Returns:
        All items across all pages as a flat list
    """
    all_items = []
    next_token = None
    page_count = 0

    while True:
        query = dict(params or {})
        if next_token:
            query["token"] = next_token

        headers = await get_auth_headers()

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(base_url, headers=headers, params=query)

        if response.status_code != 200:
            raise Exception(
                f"BTP API error {response.status_code}\n"
                f"URL: {base_url}\n"
                f"Response: {response.text[:400]}"
            )

        data = response.json()
        items = data.get("items", [])
        all_items.extend(items)
        page_count += 1

        # BTP includes "token" when there is a next page
        next_token = data.get("token")
        if not next_token:
            break

    print(f"  [btp] {base_url.split('/')[-1]}: {len(all_items)} items ({page_count} page(s))")
    return all_items


# ── 1. Service Offerings ───────────────────────────────────────────────────

async def get_service_offerings() -> list[ServiceOffering]:
    """
    Returns all BTP service offerings available in your account.

    A service offering is a BTP service like:
      hana-cloud, destination, aicore, event-mesh, xsuaa ...

    Cached for CACHE_TTL_SECONDS (default 5 min).
    """
    cache_key = "service_offerings"

    cached = get_cached(cache_key)
    if cached is not None:
        print(f"  [cache] HIT: {cache_key} ({len(cached)} items)")
        return cached

    print(f"  [cache] MISS: {cache_key} — fetching from BTP...")

    url = f"{settings.btp_sm_url}/v1/service_offerings"
    raw_items = await _get_all_pages(url)

    offerings = [
        ServiceOffering(
            id=item.get("id", ""),
            name=item.get("name", ""),
            description=item.get("description", ""),
            tags=item.get("tags") or [],
            catalog_name=item.get("catalog_name", ""),
            bindable=item.get("bindable", True),
        )
        for item in raw_items
    ]

    set_cached(cache_key, offerings)
    return offerings


# ── 2. Service Plans ───────────────────────────────────────────────────────

async def get_service_plans(offering_id: str) -> list[ServicePlan]:
    """
    Returns all plans for a specific service offering.

    Plans define what you get and at what cost.
    Example: hana-cloud has plans "hana", "hana-free", "relational-data-lake"

    Args:
        offering_id: The ID of the service offering (from get_service_offerings)
    """
    cache_key = f"plans_{offering_id}"

    cached = get_cached(cache_key)
    if cached is not None:
        print(f"  [cache] HIT: {cache_key}")
        return cached

    print(f"  [cache] MISS: {cache_key} — fetching from BTP...")

    url = f"{settings.btp_sm_url}/v1/service_plans"
    raw_items = await _get_all_pages(
        url,
        params={"fieldQuery": f"service_offering_id eq '{offering_id}'"}
    )

    plans = [
        ServicePlan(
            id=item.get("id", ""),
            name=item.get("name", ""),
            description=item.get("description", ""),
            free=item.get("free", False),
            service_offering_id=offering_id,
        )
        for item in raw_items
    ]

    set_cached(cache_key, plans)
    return plans


# ── 3. Service Instances ───────────────────────────────────────────────────

async def get_service_instances() -> list[ServiceInstance]:
    """
    Returns all service instances provisioned in your subaccount.

    An instance is one running copy of a BTP service.
    State values: SUCCEEDED | FAILED | IN_PROGRESS

    Cached for CACHE_TTL_SECONDS.
    """
    cache_key = "service_instances"

    cached = get_cached(cache_key)
    if cached is not None:
        print(f"  [cache] HIT: {cache_key} ({len(cached)} items)")
        return cached

    print(f"  [cache] MISS: {cache_key} — fetching from BTP...")

    url = f"{settings.btp_sm_url}/v1/service_instances"
    raw_items = await _get_all_pages(url)

    instances = [
        ServiceInstance(
            id=item.get("id", ""),
            name=item.get("name", ""),
            service_plan_id=item.get("service_plan_id", ""),
            # State is nested inside last_operation
            state=item.get("last_operation", {}).get("state", "UNKNOWN"),
            created_at=item.get("created_at", ""),
            updated_at=item.get("updated_at", ""),
        )
        for item in raw_items
    ]

    set_cached(cache_key, instances)
    return instances


# ── 4. Destinations ────────────────────────────────────────────────────────

async def get_destinations() -> list[Destination]:
    """
    Returns all destinations configured in your BTP subaccount.

    A destination = a saved connection to an external system.
    Instead of hardcoding URLs in your app, you define a destination
    and reference it by name.

    Common types:   HTTP (REST/OData), RFC (on-premise SAP via Cloud Connector)
    Common auth:    NoAuthentication, BasicAuthentication,
                    OAuth2ClientCredentials, PrincipalPropagation

    Cached for CACHE_TTL_SECONDS.
    """
    cache_key = f"destinations_{settings.btp_subaccount_id}"

    cached = get_cached(cache_key)
    if cached is not None:
        print(f"  [cache] HIT: {cache_key} ({len(cached)} items)")
        return cached

    print(f"  [cache] MISS: {cache_key} — fetching from BTP...")

    url = (
        f"{settings.btp_destination_url}"
        f"/destination-configuration/v1/subaccountDestinations"
    )
    headers = await get_auth_headers()

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)

    # 404 = no destinations configured yet — perfectly normal
    if response.status_code == 404:
        print("  [btp] No destinations found (none configured yet)")
        set_cached(cache_key, [])
        return []

    if response.status_code != 200:
        raise Exception(
            f"Destination API error {response.status_code}\n"
            f"URL: {url}\n"
            f"Response: {response.text[:400]}"
        )

    # Destination API returns a flat list, not wrapped in {"items": [...]}
    raw_list = response.json()
    if isinstance(raw_list, dict):
        raw_list = raw_list.get("subaccountDestinations", [])

    destinations = [
        Destination(
            name=item.get("Name", ""),           # Note: capital N — BTP quirk
            type=item.get("Type", ""),
            url=item.get("URL", ""),
            authentication=item.get("Authentication", ""),
            proxy_type=item.get("ProxyType", ""),
            description=item.get("Description", ""),
        )
        for item in raw_list
    ]

    print(f"  [btp] Destinations: {len(destinations)} found")
    set_cached(cache_key, destinations)
    return destinations


# ── ENTITLEMENTS — commented out, re-enable when CIS key is ready ──────────
#
# The Entitlements API requires a separate Cloud Management Service (CIS)
# instance with the "central" plan and its own OAuth2 client credentials.
#
# To re-enable:
#   1. Create CIS Central service instance + service key in BTP Cockpit
#   2. Add BTP_CIS_CLIENT_ID, BTP_CIS_CLIENT_SECRET, BTP_CIS_TOKEN_URL to .env
#   3. Uncomment the config entries in config.py
#   4. Uncomment the get_cis_headers() function in auth.py
#   5. Uncomment this function and the import for EntitlementItem above
#   6. Uncomment the get_btp_entitlements tool in server.py
#
# async def get_entitlements() -> list[EntitlementItem]:
#     """
#     Returns what your BTP subaccount is entitled (allowed) to use.
#
#     Entitlements define which service plans your subaccount can create
#     instances of. Without an entitlement, even if a service exists in
#     the global catalog, you cannot provision it.
#
#     The Entitlements API is a BTP core service — it always lives at:
#       https://entitlements-service.cfapps.eu10.hana.ondemand.com
#     regardless of your subaccount region.
#
#     Requires: CIS Central credentials (BTP_CIS_CLIENT_ID / BTP_CIS_CLIENT_SECRET)
#     """
#     cache_key = f"entitlements_{settings.btp_subaccount_id}"
#
#     cached = get_cached(cache_key)
#     if cached is not None:
#         print(f"  [cache] HIT: {cache_key} ({len(cached)} items)")
#         return cached
#
#     print(f"  [cache] MISS: {cache_key} — fetching from BTP...")
#
#     url = (
#         f"{settings.btp_entitlements_url}"
#         f"/entitlements/v1/subaccountAssignments"
#         f"?subaccountGUID={settings.btp_subaccount_id}"
#     )
#     from auth import get_cis_headers
#     headers = await get_cis_headers()
#
#     async with httpx.AsyncClient(timeout=30) as client:
#         response = await client.get(url, headers=headers)
#
#     if response.status_code != 200:
#         raise Exception(
#             f"Entitlements API error {response.status_code}\n"
#             f"URL: {url}\n"
#             f"Response: {response.text[:400]}\n"
#             f"Hint: Check BTP_CIS_CLIENT_ID and BTP_CIS_CLIENT_SECRET in .env\n"
#             f"Hint: Make sure CIS instance uses the 'central' plan (not 'local')\n"
#             f"Hint: Entitlements URL must be eu10 regardless of your subaccount region"
#         )
#
#     data = response.json()
#
#     # Response shape: entitledServices → servicePlans → assignmentInfo
#     entitlements = []
#     for service in data.get("entitledServices", []):
#         service_name = service.get("name", "")
#         for plan in service.get("servicePlans", []):
#             plan_name = plan.get("name", "")
#             assignments = plan.get("assignmentInfo", [{}])
#             assignment = assignments[0] if assignments else {}
#             amount = assignment.get("amount")
#             entitlements.append(
#                 EntitlementItem(
#                     service_name=service_name,
#                     plan_name=plan_name,
#                     quota=amount,
#                     unlimited=(amount is None),
#                 )
#             )
#
#     print(f"  [btp] Entitlements: {len(entitlements)} found")
#     set_cached(cache_key, entitlements)
#     return entitlements
#
# ── end of commented entitlements section ─────────────────────────────────