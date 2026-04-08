"""
models.py — Typed data models for BTP API responses.

NEW in Phase 2. This file didn't exist in Phase 1.

Why Pydantic models instead of plain dicts?
  - They validate the data automatically (catches BTP API surprises)
  - They document exactly what fields each response has
  - They give you autocomplete in your IDE
  - The AI agent gets cleaner, predictable data

How they work:
  - We define a class for each BTP concept (Service, Instance, Entitlement, etc.)
  - We pass raw BTP JSON into the class — Pydantic validates and converts it
  - We return the typed object instead of a raw dict

Field defaults:
  Most fields have a default (empty string, empty list, False, etc.)
  This handles cases where BTP doesn't return every field — instead of
  a KeyError crash, we get a sensible default.
"""

from pydantic import BaseModel, Field


# ── Service Manager Models ─────────────────────────────────────────────────

class ServiceOffering(BaseModel):
    """
    One BTP service from the service catalog.
    Example: "hana-cloud", "destination", "aicore", "event-mesh"
    """
    id: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)

    # catalog_name is sometimes different from name
    # e.g. name="hana-cloud", catalog_name="SAP HANA Cloud"
    catalog_name: str = ""

    # Whether this service can be bound to an application
    bindable: bool = True


class ServicePlan(BaseModel):
    """
    A pricing/configuration plan within a service offering.
    Every service has at least one plan.
    Example: hana-cloud has plans "hana", "relational-data-lake", etc.
    """
    id: str = ""
    name: str = ""
    description: str = ""
    free: bool = False          # True if this plan costs nothing
    service_offering_id: str = ""


class ServiceInstance(BaseModel):
    """
    A service instance = one provisioned copy of a BTP service.
    Example: your HANA Cloud database, your Destination service instance.
    """
    id: str = ""
    name: str = ""              # The name YOU gave it when creating
    service_plan_id: str = ""
    state: str = ""             # SUCCEEDED | FAILED | IN_PROGRESS
    created_at: str = ""
    updated_at: str = ""


# ── Entitlements Models ────────────────────────────────────────────────────

class EntitlementItem(BaseModel):
    """
    One entitlement = the right to use one service plan.
    Your subaccount can only use services it's entitled to.

    Example:
      service_name = "hana-cloud"
      plan_name    = "hana"
      quota        = 1          (you can create 1 HANA instance)
      unlimited    = False
    """
    service_name: str = ""
    plan_name: str = ""

    # How many instances you can create
    # None means unlimited (some plans have no hard limit)
    quota: int | None = None
    unlimited: bool = False

    @property
    def quota_display(self) -> str:
        """Human-readable quota string for display."""
        if self.unlimited:
            return "unlimited"
        if self.quota is not None:
            return str(self.quota)
        return "unknown"


# ── Destination Models ─────────────────────────────────────────────────────

class Destination(BaseModel):
    """
    A BTP Destination = a configured connection to an external system.

    BTP uses destinations to abstract connection details.
    Instead of hardcoding URLs and credentials in your app,
    you define a named destination and reference it by name.

    Examples:
      - S4HANA_PROD   → connects to your S/4HANA production system
      - BACKEND_API   → connects to a REST API
      - ECC_RFC       → connects to an on-premise SAP system via RFC
    """
    name: str = ""

    # Type of connection: HTTP | RFC | LDAP | MAIL
    type: str = ""

    # The target URL (for HTTP destinations)
    url: str = ""

    # How authentication works when connecting to the target
    # Common values: NoAuthentication, BasicAuthentication,
    #                OAuth2ClientCredentials, PrincipalPropagation
    authentication: str = ""

    # Internet = cloud/external system
    # OnPremise = on-premise system accessed via Cloud Connector
    proxy_type: str = ""

    description: str = ""