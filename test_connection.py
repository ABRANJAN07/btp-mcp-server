"""
test_connection.py — Run this BEFORE the MCP server.

This script verifies three things independently:
  1. Can we load the .env file?
  2. Can we get an OAuth2 token from BTP?
  3. Can we call the BTP Service Manager API?

Run it with:
  python test_connection.py

If all three checks pass, your BTP connection is working
and you're ready to run the MCP server.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "btp_mcp"))

from btp_mcp.config import settings
from btp_mcp.auth import get_access_token
from btp_mcp.btp_client import get_service_offerings, get_service_instances


async def main():
    print("=" * 50)
    print("BTP Connection Test — Phase 1")
    print("=" * 50)

    # ── Check 1: Config ──────────────────────────────
    print("\n[1/3] Checking configuration...")
    try:
        settings.validate()
        print(f"  ✓ BTP_CLIENT_ID    : {settings.btp_client_id[:20]}...")
        print(f"  ✓ BTP_TOKEN_URL    : {settings.btp_token_url}")
        print(f"  ✓ BTP_SM_URL       : {settings.btp_sm_url}")
    except ValueError as e:
        print(f"  ✗ Config error: {e}")
        sys.exit(1)

    # ── Check 2: Token ───────────────────────────────
    print("\n[2/3] Fetching OAuth2 token from BTP...")
    try:
        token = await get_access_token()
        # Show just the start of the token — don't print the full thing
        print(f"  ✓ Token received: {token[:40]}...")
        print(f"  ✓ Token length: {len(token)} characters")
    except Exception as e:
        print(f"  ✗ Token fetch failed: {e}")
        print("\n  Hints:")
        print("  - Check BTP_CLIENT_ID and BTP_CLIENT_SECRET in your .env")
        print("  - Check BTP_TOKEN_URL ends with /oauth/token")
        sys.exit(1)

    # ── Check 3: Service Offerings API ───────────────
    print("\n[3/3] Calling BTP Service Manager API...")
    try:
        services = await get_service_offerings()
        print(f"  ✓ Retrieved {len(services)} service offerings")

        # Show first 5 service names as a preview
        print("\n  First 5 services found:")
        for svc in services[:5]:
            print(f"    - {svc.get('name', 'unknown')}: {svc.get('description', '')[:60]}")

    except Exception as e:
        print(f"  ✗ API call failed: {e}")
        print("\n  Hints:")
        print("  - Check BTP_SM_URL in your .env")
        print("  - Make sure your service key has the 'subaccount-admin' plan")
        sys.exit(1)

    # ── Check 4: Service Instances ───────────────────
    print("\n[bonus] Checking service instances...")
    try:
        instances = await get_service_instances()
        print(f"  ✓ Retrieved {len(instances)} service instances")
        if instances:
            print("\n  Instances found:")
            for inst in instances[:5]:
                state = inst.get("last_operation", {}).get("state", "UNKNOWN")
                print(f"    - {inst.get('name', 'unknown')} [{state}]")
        else:
            print("  (No instances yet — that's fine for a fresh trial account)")
    except Exception as e:
        print(f"  ✗ Instances call failed: {e}")
        # Not a hard failure — continue

    print("\n" + "=" * 50)
    print("✓ All checks passed! BTP connection is working.")
    print("\nNext step: Connect Claude Code to the MCP server.")
    print("See README.md for instructions.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())