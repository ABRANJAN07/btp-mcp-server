"""
server.py — The MCP server for Phase 2.

Active tools (5):
  1. list_btp_services      — browse the BTP service catalog
  2. get_service_plans      — plans for a specific service
  3. list_btp_instances     — what is running in your subaccount
  4. get_btp_destinations   — configured external connections
  5. recommend_btp_service  — AI-assisted recommendation

NOTE — get_btp_entitlements is commented out:
  It requires a separate CIS Central service key.
  The tool code is preserved below. Re-enable it by:
    1. Following ENTITLEMENTS_SETUP.md to create the CIS service key
    2. Uncommenting the tool function and its import below
    3. Uncommenting related code in config.py, auth.py, btp_client.py

How the 5 active tools relate to each other:
  list_btp_services    → What BTP services EXIST globally?
  get_service_plans    → What plans does service X have?
  list_btp_instances   → What is actually RUNNING in my subaccount?
  get_btp_destinations → What external connections are configured?
  recommend_btp_service→ Given a need, what should I use + is it running?
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "btp_mcp"))

from fastmcp import FastMCP
from btp_mcp.config import settings
from btp_mcp.cache import cache_info
from btp_mcp.btp_client import (
    get_service_offerings,
    get_service_plans,
    get_service_instances,
    get_destinations,
    # get_entitlements,  # commented out — re-enable with CIS key
)

# Create the MCP server
mcp = FastMCP(name="SAP BTP Discovery — Phase 2")


# ─────────────────────────────────────────────────────────────────
# Tool 1 — List all BTP services in the catalog
# ─────────────────────────────────────────────────────────────────

@mcp.tool
async def list_btp_services(keyword: str = "") -> dict:
    """
    Lists all SAP BTP services available in the global service catalog.

    These are services that EXIST in BTP — not necessarily what
    your subaccount is running. Use list_btp_instances to see
    what is actually provisioned and running.

    Optionally filter by keyword (searches name, description, and tags).

    Examples of when to use this tool:
      - "What BTP services are available?"
      - "Is there an AI service in BTP?"
      - "Show me all messaging services"
      - "Does BTP have a workflow service?"
    """
    print(f"\n[tool] list_btp_services(keyword='{keyword}')")

    offerings = await get_service_offerings()

    # Filter by keyword across name, description, and tags
    if keyword:
        kw = keyword.lower()
        offerings = [
            o for o in offerings
            if kw in o.name.lower()
            or kw in o.description.lower()
            or any(kw in tag.lower() for tag in o.tags)
        ]

    return {
        "total_found": len(offerings),
        "keyword_filter": keyword or None,
        "services": [
            {
                "name": o.name,
                "description": o.description[:200],
                "tags": o.tags,
                "bindable": o.bindable,
            }
            for o in offerings
        ],
    }


# ─────────────────────────────────────────────────────────────────
# Tool 2 — Get plans for a specific service
# ─────────────────────────────────────────────────────────────────

@mcp.tool
async def get_btp_service_plans(service_name: str) -> dict:
    """
    Returns all available plans for a specific BTP service.

    Plans differ in capacity, features, and cost. Some have a free tier.
    Use this to understand what options exist before creating an instance.

    Examples of when to use this tool:
      - "What plans does HANA Cloud have?"
      - "Is there a free plan for the Destination service?"
      - "What are the plans for SAP AI Core?"
      - "Which plan should I use for development?"

    Args:
        service_name: The service name as it appears in BTP
                      (e.g. "hana-cloud", "destination", "aicore")
    """
    print(f"\n[tool] get_btp_service_plans(service_name='{service_name}')")

    all_offerings = await get_service_offerings()

    # Find the service by name (case-insensitive partial match)
    matching = [
        o for o in all_offerings
        if service_name.lower() in o.name.lower()
    ]

    if not matching:
        return {
            "error": f"No service found matching '{service_name}'",
            "hint": "Use list_btp_services to see the exact names available",
        }

    offering = matching[0]
    plans = await get_service_plans(offering.id)

    return {
        "service_name": offering.name,
        "service_id": offering.id,
        "total_plans": len(plans),
        "plans": [
            {
                "name": p.name,
                "description": p.description[:200],
                "free": p.free,
            }
            for p in plans
        ],
    }


# ─────────────────────────────────────────────────────────────────
# Tool 3 — List service instances
# ─────────────────────────────────────────────────────────────────

@mcp.tool
async def list_btp_instances(service_name: str = "") -> dict:
    """
    Lists all service instances currently provisioned in your BTP subaccount.

    An instance is one running copy of a BTP service that you created.
    Shows the current state: SUCCEEDED (healthy), FAILED, or IN_PROGRESS.

    Examples of when to use this tool:
      - "What service instances do I have running?"
      - "Is HANA Cloud already set up in my account?"
      - "Are there any failed instances?"
      - "What's the ID of my Destination service instance?"
    """
    print(f"\n[tool] list_btp_instances(service_name='{service_name}')")

    instances = await get_service_instances()

    if service_name:
        sn = service_name.lower()
        instances = [i for i in instances if sn in i.name.lower()]

    # Count by state — useful health summary
    state_counts: dict[str, int] = {}
    for inst in instances:
        state_counts[inst.state] = state_counts.get(inst.state, 0) + 1

    return {
        "total_found": len(instances),
        "service_filter": service_name or None,
        "state_summary": state_counts,
        "instances": [
            {
                "name": i.name,
                "id": i.id,
                "state": i.state,
                "created_at": i.created_at,
            }
            for i in instances
        ],
    }


# ─────────────────────────────────────────────────────────────────
# Tool 4 — Get BTP destinations
# ─────────────────────────────────────────────────────────────────

@mcp.tool
async def get_btp_destinations(proxy_type: str = "", auth_type: str = "") -> dict:
    """
    Lists all destinations configured in your BTP subaccount.

    A destination is a saved connection to an external system.
    Instead of hardcoding URLs in your code, you define a named
    destination in BTP and reference it by name.

    Filter options:
      proxy_type: "OnPremise" (via Cloud Connector) or "Internet" (cloud)
      auth_type:  e.g. "OAuth2ClientCredentials", "BasicAuthentication"

    Examples of when to use this tool:
      - "What destinations are configured in BTP?"
      - "Is there a destination for our S/4HANA system?"
      - "Show me all on-premise destinations"
      - "What authentication does the ERP destination use?"
    """
    print(f"\n[tool] get_btp_destinations(proxy_type='{proxy_type}', auth_type='{auth_type}')")

    destinations = await get_destinations()

    if proxy_type:
        destinations = [
            d for d in destinations
            if proxy_type.lower() in d.proxy_type.lower()
        ]
    if auth_type:
        destinations = [
            d for d in destinations
            if auth_type.lower() in d.authentication.lower()
        ]

    return {
        "total_found": len(destinations),
        "filters_applied": {
            "proxy_type": proxy_type or None,
            "auth_type": auth_type or None,
        },
        "destinations": [
            {
                "name": d.name,
                "type": d.type,
                "url": d.url,
                "authentication": d.authentication,
                "proxy_type": d.proxy_type,
                "description": d.description,
            }
            for d in destinations
        ],
    }


# ─────────────────────────────────────────────────────────────────
# Tool 5 — Recommend a BTP service for a use case
# ─────────────────────────────────────────────────────────────────

# Simple keyword → service name mapping.
# Phase 5 replaces this with RAG over SAP Discovery Center content.
_USE_CASE_MAP = {
    "messaging":   ["event-mesh", "enterprise-messaging"],
    "event":       ["event-mesh", "enterprise-messaging"],
    "database":    ["hana-cloud"],
    "hana":        ["hana-cloud"],
    "sql":         ["hana-cloud"],
    "ai":          ["aicore", "generative-ai-hub"],
    "llm":         ["aicore", "generative-ai-hub"],
    "machine":     ["aicore"],
    "workflow":    ["workflow", "process-automation"],
    "process":     ["process-automation"],
    "integration": ["integration-suite"],
    "api":         ["integration-suite", "api-management"],
    "auth":        ["xsuaa", "authorization-and-trust-management"],
    "login":       ["xsuaa"],
    "destination": ["destination"],
    "connect":     ["destination", "connectivity"],
    "onpremise":   ["connectivity"],
    "storage":     ["objectstore"],
    "file":        ["objectstore"],
    "monitoring":  ["cloud-logging", "alert-notification"],
    "alert":       ["alert-notification"],
    "logging":     ["cloud-logging"],
}


@mcp.tool
async def recommend_btp_service(use_case: str) -> dict:
    """
    Recommends the right BTP service(s) for a described use case.
    Also checks whether the recommended services are already running
    as instances in your subaccount.

    Note: Entitlement checking is temporarily disabled.
    The 'is_entitled' field always shows null until re-enabled.

    Examples of when to use this tool:
      - "What BTP service should I use for async messaging?"
      - "I need to store files in BTP — what service do I use?"
      - "How do I call an LLM from my CAP app?"
      - "What service handles OAuth2 auth in BTP?"
      - "I need to connect to an on-premise SAP system"
    """
    print(f"\n[tool] recommend_btp_service(use_case='{use_case}')")

    use_case_lower = use_case.lower()

    # Match keywords from use case description
    recommended_names: list[str] = []
    matched_keywords: list[str] = []

    for keyword, service_names in _USE_CASE_MAP.items():
        if keyword in use_case_lower:
            for name in service_names:
                if name not in recommended_names:
                    recommended_names.append(name)
            matched_keywords.append(keyword)

    if not recommended_names:
        return {
            "use_case": use_case,
            "matched": False,
            "message": (
                "No specific BTP service matched this use case. "
                "Try list_btp_services with a keyword to search the full catalog."
            ),
            "recommendations": [],
        }

    # Check which recommended services have running instances
    all_instances = await get_service_instances()
    running_names = {
        i.name.lower()
        for i in all_instances
        if i.state == "SUCCEEDED"
    }

    recommendations = []
    for name in recommended_names:
        name_lower = name.lower()
        has_instance = any(name_lower in r for r in running_names)

        # Determine what action is needed
        if has_instance:
            action = "already running — ready to use"
        else:
            action = "not yet provisioned — create an instance to use it"

        recommendations.append({
            "service_name": name,
            "has_running_instance": has_instance,
            # is_entitled is null until Entitlements API is re-enabled
            "is_entitled": None,
            "action_needed": action,
        })

    return {
        "use_case": use_case,
        "matched": True,
        "matched_on_keywords": matched_keywords,
        "note": "Entitlement check is temporarily disabled. Only instance status is shown.",
        "recommendations": recommendations,
    }


# ── ENTITLEMENTS TOOL — commented out, re-enable when CIS key is ready ─────
#
# @mcp.tool
# async def get_btp_entitlements(service_filter: str = "") -> dict:
#     """
#     Returns what your BTP subaccount is entitled (allowed) to use.
#
#     Entitlements define which service plans your subaccount can provision.
#     Without an entitlement, you cannot create an instance of that service
#     even if it exists in the global catalog.
#
#     NOTE: This tool requires a Cloud Management Service (CIS) Central
#     service key. See ENTITLEMENTS_SETUP.md to set it up.
#
#     Examples:
#       - "What services am I entitled to use?"
#       - "Do I have HANA Cloud entitlement?"
#       - "What's my quota for the destination service?"
#     """
#     print(f"\n[tool] get_btp_entitlements(service_filter='{service_filter}')")
#
#     from btp_client import get_entitlements
#     entitlements = await get_entitlements()
#
#     if service_filter:
#         sf = service_filter.lower()
#         entitlements = [e for e in entitlements if sf in e.service_name.lower()]
#
#     return {
#         "total_found": len(entitlements),
#         "service_filter": service_filter or None,
#         "subaccount_id": settings.btp_subaccount_id,
#         "entitlements": [
#             {
#                 "service": e.service_name,
#                 "plan": e.plan_name,
#                 "quota": e.quota_display,
#             }
#             for e in entitlements
#         ],
#     }
#
# ── end of commented entitlements section ─────────────────────────────────


# ─────────────────────────────────────────────────────────────────
# Start the server
# ─────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     # Validate config here — only runs on server start, not when tests import
#     settings.validate()

#     info = cache_info()
#     print("SAP BTP Discovery MCP Server — Phase 2")
#     print("Active tools (5):")
#     print("  list_btp_services, get_btp_service_plans, list_btp_instances,")
#     print("  get_btp_destinations, recommend_btp_service")
#     print("Inactive (pending CIS key):")
#     print("  get_btp_entitlements")
#     print(f"Cache TTL: {info['ttl_seconds']}s | Transport: stdio\n")
#     print(f"Cache TTL: {info['ttl_seconds']}s | Transport: stdio\n")
#     mcp.run(transport="stdio")

### Alternative main() function for CLI command
def main():
    """
    Entry point for the installed CLI command.
    Called when user runs: btp-mcp-server
    This is what pyproject.toml points to:
      [project.scripts]
      btp-mcp-server = "btp_mcp.server:main"
    """
    settings.validate()
    info = cache_info()
    print("SAP BTP Discovery MCP Server — Phase 2")
    print("Active tools (5):")
    print("  list_btp_services, get_btp_service_plans, list_btp_instances,")
    print("  get_btp_destinations, recommend_btp_service")
    print("Inactive (pending CIS key):")
    print("  get_btp_entitlements")
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()