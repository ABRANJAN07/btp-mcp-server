"""
server.py — The MCP server for Phase 1.

This is the entry point. When you run `python server.py`,
it starts the MCP server and waits for an AI agent (like Claude Code)
to connect and call our tools.

We define 2 tools in Phase 1:
  1. list_btp_services   — shows all available BTP services
  2. list_btp_instances  — shows all service instances in your subaccount

How MCP works (simply):
  - An AI agent (Claude Code, Cursor, etc.) connects to this server
  - The agent reads the tool names and descriptions
  - When the user asks a question, the agent decides which tool to call
  - The tool runs, returns data, and the agent uses it to answer

Transport mode = "stdio" means:
  - The AI agent launches this script as a subprocess
  - They communicate via stdin/stdout (standard input/output)
  - No network port needed — it's a direct pipe
"""

import asyncio

from fastmcp import FastMCP
from btp_mcp.config import settings
from btp_mcp.btp_client import get_service_offerings, get_service_instances


# Validate config on startup — fail fast if .env is missing values
settings.validate()

# Create the MCP server
# The name shows up in the AI agent's tool list
mcp = FastMCP(name="SAP BTP Discovery")


# ─────────────────────────────────────────────
# Tool 1 — List available BTP services
# ─────────────────────────────────────────────

@mcp.tool
async def list_btp_services(keyword: str = "") -> dict:
    """
    Lists all SAP BTP services available in your account.

    Optionally filter by keyword to narrow results.
    Use this when the user asks what services BTP offers,
    or wants to find a specific type of service (e.g. 'database', 'messaging').

    Examples:
      - "What services does BTP have?"
      - "Is there a messaging service available?"
      - "Find me AI-related BTP services"
    """
    print(f"\n[tool] list_btp_services called (keyword='{keyword}')")

    # Fetch all services from BTP
    all_services = await get_service_offerings()

    # If a keyword was given, filter the list
    if keyword:
        kw = keyword.lower()
        filtered = [
            s for s in all_services
            if kw in s.get("name", "").lower()
            or kw in s.get("description", "").lower()
            or any(kw in tag.lower() for tag in s.get("tags", []))
        ]
    else:
        filtered = all_services

    # Return a clean, readable structure
    # We pick only the fields that are actually useful for an AI agent
    return {
        "total_found": len(filtered),
        "keyword_filter": keyword if keyword else None,
        "services": [
            {
                "name": s.get("name", ""),
                "description": s.get("description", "")[:200],  # truncate long descriptions
                "tags": s.get("tags", []),
            }
            for s in filtered
        ],
    }


# ─────────────────────────────────────────────
# Tool 2 — List service instances
# ─────────────────────────────────────────────

@mcp.tool
async def list_btp_instances(service_name: str = "") -> dict:
    """
    Lists all service instances currently provisioned in your BTP subaccount.
    Shows their name, status (SUCCEEDED / FAILED / IN_PROGRESS), and creation date.

    Optionally filter by service name to check a specific service.
    Use this when the user wants to know what is actually running.

    Examples:
      - "What service instances do I have?"
      - "Is HANA Cloud already set up in my account?"
      - "Are there any failed service instances?"
    """
    print(f"\n[tool] list_btp_instances called (service_name='{service_name}')")

    all_instances = await get_service_instances()

    # Filter by service name if provided
    if service_name:
        sn = service_name.lower()
        filtered = [
            i for i in all_instances
            if sn in i.get("name", "").lower()
        ]
    else:
        filtered = all_instances

    # Summarise by state so the AI can quickly see health at a glance
    state_counts = {}
    for instance in filtered:
        state = instance.get("last_operation", {}).get("state", "UNKNOWN")
        state_counts[state] = state_counts.get(state, 0) + 1

    return {
        "total_found": len(filtered),
        "service_filter": service_name if service_name else None,
        "summary": state_counts,   # e.g. {"SUCCEEDED": 3, "FAILED": 1}
        "instances": [
            {
                "name": i.get("name", ""),
                "id": i.get("id", ""),
                "state": i.get("last_operation", {}).get("state", "UNKNOWN"),
                "created_at": i.get("created_at", ""),
            }
            for i in filtered
        ],
    }


# ─────────────────────────────────────────────
# Start the server
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("SAP BTP Discovery MCP Server — Phase 1")
    print("Tools registered: list_btp_services, list_btp_instances")
    print("Transport: stdio — waiting for MCP client to connect...\n")
    mcp.run(transport="stdio")