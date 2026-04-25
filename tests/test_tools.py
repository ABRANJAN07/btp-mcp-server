"""
tests/test_tools.py — Test suite for Phase 2 MCP tools.

Active tests (15):
  - TestListBtpServices      (5 tests)
  - TestListBtpInstances     (4 tests)
  - TestGetBtpDestinations   (4 tests)
  - TestRecommendBtpService  (3 tests) — adjusted for no entitlement check

NOTE — Entitlements tests commented out:
  TestGetBtpEntitlements is preserved below but commented out.
  Re-enable it when the CIS Central service key is set up.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "btp_mcp"))

from unittest.mock import patch, AsyncMock
from btp_mcp.models import ServiceOffering, ServicePlan, ServiceInstance, Destination

# ── Shared test data ───────────────────────────────────────────────────────

FAKE_OFFERINGS = [
    ServiceOffering(id="o1", name="hana-cloud",  description="In-memory database", tags=["database", "hana", "sql"]),
    ServiceOffering(id="o2", name="event-mesh",  description="Async messaging",    tags=["messaging", "event"]),
    ServiceOffering(id="o3", name="aicore",      description="AI and ML runtime",  tags=["ai", "ml", "llm"]),
    ServiceOffering(id="o4", name="destination", description="Manage connections", tags=["connectivity"]),
]

FAKE_PLANS = [
    ServicePlan(id="p1", name="hana",      description="Full HANA Cloud", free=False, service_offering_id="o1"),
    ServicePlan(id="p2", name="hana-free", description="Free tier",       free=True,  service_offering_id="o1"),
]

FAKE_INSTANCES = [
    ServiceInstance(id="i1", name="hana-cloud-dev",  service_plan_id="p1", state="SUCCEEDED",   created_at="2024-01-01"),
    ServiceInstance(id="i2", name="my-event-mesh",   service_plan_id="p3", state="SUCCEEDED",   created_at="2024-01-02"),
    ServiceInstance(id="i3", name="failing-service", service_plan_id="p5", state="FAILED",      created_at="2024-01-03"),
]

FAKE_DESTINATIONS = [
    Destination(name="S4HANA_PROD", type="HTTP", url="https://s4.example.com", authentication="OAuth2ClientCredentials", proxy_type="Internet",  description="Production S/4HANA"),
    Destination(name="ECC_ONPREM",  type="RFC",  url="",                       authentication="BasicAuthentication",      proxy_type="OnPremise", description="On-premise ECC"),
]


# ── Tool 1: list_btp_services ──────────────────────────────────────────────

class TestListBtpServices:

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_offerings", new_callable=AsyncMock, return_value=FAKE_OFFERINGS)
    async def test_returns_all_services_no_keyword(self, _):
        from btp_mcp.server import list_btp_services
        result = await list_btp_services(keyword="")
        assert result["total_found"] == 4
        assert result["keyword_filter"] is None
        names = [s["name"] for s in result["services"]]
        assert "hana-cloud" in names
        assert "event-mesh" in names

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_offerings", new_callable=AsyncMock, return_value=FAKE_OFFERINGS)
    async def test_keyword_filter_by_name(self, _):
        from btp_mcp.server import list_btp_services
        result = await list_btp_services(keyword="hana")
        assert result["total_found"] == 1
        assert result["services"][0]["name"] == "hana-cloud"

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_offerings", new_callable=AsyncMock, return_value=FAKE_OFFERINGS)
    async def test_keyword_filter_by_tag(self, _):
        from btp_mcp.server import list_btp_services
        result = await list_btp_services(keyword="messaging")
        assert result["total_found"] == 1
        assert result["services"][0]["name"] == "event-mesh"

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_offerings", new_callable=AsyncMock, return_value=FAKE_OFFERINGS)
    async def test_no_match_returns_empty(self, _):
        from btp_mcp.server import list_btp_services
        result = await list_btp_services(keyword="quantum-blockchain-xyz")
        assert result["total_found"] == 0
        assert result["services"] == []

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_offerings", new_callable=AsyncMock, return_value=FAKE_OFFERINGS)
    async def test_keyword_is_case_insensitive(self, _):
        from btp_mcp.server import list_btp_services
        upper = await list_btp_services(keyword="HANA")
        lower = await list_btp_services(keyword="hana")
        assert upper["total_found"] == lower["total_found"]


# ── Tool 3: list_btp_instances ─────────────────────────────────────────────

class TestListBtpInstances:

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_returns_all_instances(self, _):
        from btp_mcp.server import list_btp_instances
        result = await list_btp_instances(service_name="")
        assert result["total_found"] == 3

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_state_summary_correct(self, _):
        from btp_mcp.server import list_btp_instances
        result = await list_btp_instances()
        assert result["state_summary"]["SUCCEEDED"] == 2
        assert result["state_summary"]["FAILED"] == 1

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_filter_by_service_name(self, _):
        from btp_mcp.server import list_btp_instances
        result = await list_btp_instances(service_name="hana")
        assert result["total_found"] == 1
        assert result["instances"][0]["name"] == "hana-cloud-dev"

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_no_match_returns_empty(self, _):
        from btp_mcp.server import list_btp_instances
        result = await list_btp_instances(service_name="nonexistent-xyz")
        assert result["total_found"] == 0
        assert result["instances"] == []


# ── Tool 4: get_btp_destinations ───────────────────────────────────────────

class TestGetBtpDestinations:

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_destinations", new_callable=AsyncMock, return_value=FAKE_DESTINATIONS)
    async def test_returns_all_destinations(self, _):
        from btp_mcp.server import get_btp_destinations
        result = await get_btp_destinations()
        assert result["total_found"] == 2

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_destinations", new_callable=AsyncMock, return_value=FAKE_DESTINATIONS)
    async def test_filter_onpremise(self, _):
        from btp_mcp.server import get_btp_destinations
        result = await get_btp_destinations(proxy_type="OnPremise")
        assert result["total_found"] == 1
        assert result["destinations"][0]["name"] == "ECC_ONPREM"

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_destinations", new_callable=AsyncMock, return_value=FAKE_DESTINATIONS)
    async def test_filter_by_auth_type(self, _):
        from btp_mcp.server import get_btp_destinations
        result = await get_btp_destinations(auth_type="OAuth2")
        assert result["total_found"] == 1
        assert result["destinations"][0]["name"] == "S4HANA_PROD"

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_destinations", new_callable=AsyncMock, return_value=[])
    async def test_empty_destinations(self, _):
        from btp_mcp.server import get_btp_destinations
        result = await get_btp_destinations()
        assert result["total_found"] == 0
        assert result["destinations"] == []


# ── Tool 5: recommend_btp_service ──────────────────────────────────────────

class TestRecommendBtpService:

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_messaging_recommends_event_mesh(self, _):
        from btp_mcp.server import recommend_btp_service
        result = await recommend_btp_service(use_case="I need async messaging between services")
        assert result["matched"] is True
        names = [r["service_name"] for r in result["recommendations"]]
        assert "event-mesh" in names

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_shows_running_instance_status(self, _):
        from btp_mcp.server import recommend_btp_service
        result = await recommend_btp_service(use_case="I need a hana database")
        recs = {r["service_name"]: r for r in result["recommendations"]}
        assert "hana-cloud" in recs
        # hana-cloud-dev is in FAKE_INSTANCES with SUCCEEDED state
        # "hana-cloud" is a substring of "hana-cloud-dev" so it matches
        assert recs["hana-cloud"]["has_running_instance"] is True
        assert "already running" in recs["hana-cloud"]["action_needed"]

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_unknown_use_case_returns_not_matched(self, _):
        from btp_mcp.server import recommend_btp_service
        result = await recommend_btp_service(use_case="help me plan a birthday party")
        assert result["matched"] is False
        assert result["recommendations"] == []
        assert "message" in result

    @pytest.mark.asyncio
    @patch("btp_mcp.server.get_service_instances", new_callable=AsyncMock, return_value=FAKE_INSTANCES)
    async def test_is_entitled_is_null_when_disabled(self, _):
        """Entitlement check is disabled — is_entitled should always be None."""
        from btp_mcp.server import recommend_btp_service
        result = await recommend_btp_service(use_case="I need messaging")
        for rec in result["recommendations"]:
            assert rec["is_entitled"] is None


# ── ENTITLEMENTS TESTS — commented out, re-enable with CIS key ─────────────
#
# from models import EntitlementItem
#
# FAKE_ENTITLEMENTS = [
#     EntitlementItem(service_name="hana-cloud",  plan_name="hana",    quota=1,    unlimited=False),
#     EntitlementItem(service_name="event-mesh",  plan_name="default", quota=None, unlimited=True),
#     EntitlementItem(service_name="destination", plan_name="lite",    quota=1,    unlimited=False),
# ]
#
# class TestGetBtpEntitlements:
#
#     @pytest.mark.asyncio
#     @patch("btp_mcp.server.get_entitlements", new_callable=AsyncMock, return_value=FAKE_ENTITLEMENTS)
#     async def test_returns_all_entitlements(self, _):
#         from btp_mcp.server import get_btp_entitlements
#         result = await get_btp_entitlements(service_filter="")
#         assert result["total_found"] == 3
#
#     @pytest.mark.asyncio
#     @patch("btp_mcp.server.get_entitlements", new_callable=AsyncMock, return_value=FAKE_ENTITLEMENTS)
#     async def test_filter_by_service(self, _):
#         from btp_mcp.server import get_btp_entitlements
#         result = await get_btp_entitlements(service_filter="hana")
#         assert result["total_found"] == 1
#         assert result["entitlements"][0]["service"] == "hana-cloud"
#         assert result["entitlements"][0]["quota"] == "1"
#
#     @pytest.mark.asyncio
#     @patch("btp_mcp.server.get_entitlements", new_callable=AsyncMock, return_value=FAKE_ENTITLEMENTS)
#     async def test_unlimited_quota_shown_correctly(self, _):
#         from btp_mcp.server import get_btp_entitlements
#         result = await get_btp_entitlements(service_filter="event")
#         assert result["entitlements"][0]["quota"] == "unlimited"
#
# ── end of commented entitlements tests ────────────────────────────────────