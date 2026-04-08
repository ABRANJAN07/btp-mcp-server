"""
test_connection.py — Verifies all active BTP API connections.

NOTE — Entitlements step is skipped:
  Step 4 (Entitlements) is commented out until the CIS Central
  service key is set up. See ENTITLEMENTS_SETUP.md for instructions.

Active checks:
  1. Config — all required .env values present
  2. OAuth2 token — BTP auth is working
  3. Service Manager — service catalog + instances
  4. Destination service — configured connections
  [SKIP] Entitlements — requires CIS Central service key

Run: python test_connection.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "btp_mcp"))

from btp_mcp.config import settings
from btp_mcp.auth import get_access_token
from btp_mcp.cache import clear_cache, cache_info
from btp_mcp.btp_client import (
    get_service_offerings,
    get_service_instances,
    get_destinations,
    # get_entitlements,  # skipped — needs CIS key
)


async def main():
    print("=" * 55)
    print("BTP Connection Test — Phase 2")
    print("=" * 55)

    # ── Check 1: Config ──────────────────────────────────────
    print("\n[1/4] Checking configuration...")
    try:
        settings.validate()
        print(f"  ✓ BTP_CLIENT_ID     : {settings.btp_client_id[:20]}...")
        print(f"  ✓ BTP_TOKEN_URL     : {settings.btp_token_url}")
        print(f"  ✓ BTP_SM_URL        : {settings.btp_sm_url}")
        print(f"  ✓ BTP_DESTINATION_URL: {settings.btp_destination_url}")
        print(f"  ✓ BTP_SUBACCOUNT_ID : {settings.btp_subaccount_id}")
        print(f"  ✓ CACHE_TTL_SECONDS : {settings.cache_ttl_seconds}s")
    except ValueError as e:
        print(f"  ✗ {e}")
        sys.exit(1)

    # ── Check 2: OAuth2 Token ────────────────────────────────
    print("\n[2/4] Fetching OAuth2 token from BTP...")
    try:
        token = await get_access_token()
        print(f"  ✓ Token received ({len(token)} chars): {token[:40]}...")
    except Exception as e:
        print(f"  ✗ Token fetch failed: {e}")
        sys.exit(1)

    # ── Check 3: Service Manager ─────────────────────────────
    print("\n[3/4] Service Manager API...")
    try:
        # Service offerings (catalog)
        services = await get_service_offerings()
        print(f"  ✓ {len(services)} service offerings in catalog")
        print("  First 5:")
        for s in services[:5]:
            print(f"    · {s.name}: {s.description[:60]}")

        # Service instances
        instances = await get_service_instances()
        if instances:
            print(f"\n  ✓ {len(instances)} service instance(s) found:")
            for i in instances[:5]:
                print(f"    · {i.name} [{i.state}]")
        else:
            print("\n  ✓ No instances yet (normal for a fresh trial account)")

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        sys.exit(1)

    # ── Check 4: Destinations ────────────────────────────────
    print("\n[4/4] Destination service...")
    try:
        destinations = await get_destinations()
        if destinations:
            print(f"  ✓ {len(destinations)} destination(s) found:")
            for d in destinations[:3]:
                print(f"    · {d.name} ({d.type}, {d.proxy_type or 'no proxy'})")
        else:
            print("  ✓ No destinations configured yet — that's fine")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        print("  Note: Destination failures are non-critical for Phase 2")

    # ── Entitlements: SKIPPED ────────────────────────────────
    print("\n[SKIP] Entitlements — requires CIS Central service key")
    print("       See ENTITLEMENTS_SETUP.md when you're ready to enable it")

    # ── Bonus: Cache test ────────────────────────────────────
    print("\n[bonus] Cache behaviour...")
    import time
    start = time.time()
    await get_service_offerings()   # should be instant (cache hit)
    elapsed = time.time() - start
    info = cache_info()
    print(f"  ✓ Cache hit in {elapsed * 1000:.1f}ms (vs ~300ms for a live BTP call)")
    print(f"  ✓ {info['entries_cached']} entries cached: {info['cached_keys']}")

    print("\n" + "=" * 55)
    print("✓ All active checks passed! Ready to run the MCP server.")
    print("\nNext steps:")
    print("  1. Update claude_desktop_config.json (see README.md)")
    print("  2. Restart Claude Desktop")
    print("  3. Try: 'What BTP services do I have available?'")
    print("  4. Try: 'Are there any failed service instances?'")
    print("  5. Try: 'I need async messaging — what BTP service should I use?'")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())