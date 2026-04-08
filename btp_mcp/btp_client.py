"""
btp_client.py — Calls the SAP BTP Service Manager API.

In Phase 1 we only call ONE endpoint:
  GET /v1/service_offerings
  → returns the list of all BTP services available in our account

The Service Manager API docs:
  https://api.sap.com/api/APIServiceManager/resource

We keep this file very simple — no caching, no models, just raw API calls.
Caching and Pydantic models come in Phase 2.
"""

import httpx
from .auth import get_auth_headers
from .config import settings


async def get_service_offerings() -> list[dict]:
    """
    Calls the BTP Service Manager API to get all available service offerings.

    Returns a list of services — each is a dict with keys like:
      - id
      - name         (e.g. "hana-cloud", "destination", "aicore")
      - description
      - catalog_name
      - tags         (list of strings)

    BTP returns paginated results — for Phase 1 we just get the first page.
    Pagination handling comes in Phase 2.
    """
    url = f"{settings.btp_sm_url}/v1/service_offerings"
    headers = await get_auth_headers()

    print(f"  [btp] Calling: GET {url}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)

    # If BTP returns an error, show it clearly
    if response.status_code != 200:
        raise Exception(
            f"BTP API call failed. Status: {response.status_code}\n"
            f"URL: {url}\n"
            f"Response: {response.text[:500]}"
        )

    data = response.json()

    # The actual list of services is inside the "items" key
    services = data.get("items", [])
    print(f"  [btp] Received {len(services)} service offerings")
    return services


async def get_service_instances() -> list[dict]:
    """
    Calls the BTP Service Manager API to get all service instances
    currently provisioned in the subaccount.

    Each instance has:
      - id
      - name          (the name you gave it when creating)
      - service_plan_id
      - last_operation  (contains state: SUCCEEDED / FAILED / IN_PROGRESS)
      - created_at
    """
    url = f"{settings.btp_sm_url}/v1/service_instances"
    headers = await get_auth_headers()

    print(f"  [btp] Calling: GET {url}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(
            f"BTP API call failed. Status: {response.status_code}\n"
            f"URL: {url}\n"
            f"Response: {response.text[:500]}"
        )

    data = response.json()
    instances = data.get("items", [])
    print(f"  [btp] Received {len(instances)} service instances")
    return instances