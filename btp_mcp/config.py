"""
config.py — All configuration for Phase 2.

Reads environment variables from the .env file.
All other modules import from this — never read os.environ directly.

NOTE — Entitlements API skipped for now:
  The Entitlements API requires a separate 'Cloud Management Service'
  instance with the 'central' plan, which needs an extra service key.
  This is commented out and will be re-enabled in a future phase once
  the CIS service key setup is complete.
  See: ENTITLEMENTS_SETUP.md for instructions when you're ready.
"""

import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env if present.
# First try the current working directory / parent folders, then fall back
# to the package root when running from an installed package or alternate cwd.
env_path = find_dotenv(filename=".env", usecwd=True)
if not env_path:
    env_path = os.path.join(os.path.dirname(__file__), os.pardir, ".env")

load_dotenv(env_path)


class Settings:
    """All configuration in one place."""

    # ── Service Manager credentials ────────────────────────────────────────
    # From your Service Manager (subaccount-admin) service key.
    # Used for: service catalog, service instances, service plans, destinations.
    btp_client_id: str = os.getenv("BTP_CLIENT_ID", "")
    btp_client_secret: str = os.getenv("BTP_CLIENT_SECRET", "")
    btp_token_url: str = os.getenv("BTP_TOKEN_URL", "")

    # ── BTP API base URLs ──────────────────────────────────────────────────

    # Service Manager — region-specific (matches your subaccount region)
    btp_sm_url: str = os.getenv(
        "BTP_SM_URL",
        "https://service-manager.cfapps.us10.hana.ondemand.com"
    )

    # Destination service — region-specific (matches your subaccount region)
    btp_destination_url: str = os.getenv(
        "BTP_DESTINATION_URL",
        "https://destination.cfapps.us10.hana.ondemand.com"
    )

    # ── Subaccount ─────────────────────────────────────────────────────────
    # Your BTP subaccount GUID.
    # Find it: BTP Cockpit → your subaccount → Overview → "Subaccount ID"
    btp_subaccount_id: str = os.getenv("BTP_SUBACCOUNT_ID", "")

    # ── Cache ──────────────────────────────────────────────────────────────
    # How long (seconds) to keep BTP API responses in memory before refreshing.
    # Default: 300 seconds (5 minutes). Lower during development if needed.
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # ── ENTITLEMENTS — commented out, re-enable when CIS key is ready ──────
    #
    # The Entitlements API is a separate BTP core service that requires its
    # own OAuth2 client from the Cloud Management Service (CIS) central plan.
    # Steps to enable later:
    #   1. BTP Cockpit → Service Marketplace → Cloud Management Service
    #   2. Create instance with plan: central → create service key
    #   3. Uncomment the lines below and fill in .env
    #
    # btp_cis_client_id: str = os.getenv("BTP_CIS_CLIENT_ID", "")
    # btp_cis_client_secret: str = os.getenv("BTP_CIS_CLIENT_SECRET", "")
    # btp_cis_token_url: str = os.getenv("BTP_CIS_TOKEN_URL", "")
    # btp_entitlements_url: str = os.getenv(
    #     "BTP_ENTITLEMENTS_URL",
    #     "https://entitlements-service.cfapps.eu10.hana.ondemand.com"
    #     # Note: Entitlements URL is always eu10 regardless of your subaccount region
    # )
    # ── end of commented entitlements section ─────────────────────────────

    def validate(self):
        """
        Check all required values are set.
        Called at server startup — fail fast rather than getting
        mysterious errors when a tool is actually called.
        """
        missing = []

        if not self.btp_client_id:
            missing.append("BTP_CLIENT_ID")
        if not self.btp_client_secret:
            missing.append("BTP_CLIENT_SECRET")
        if not self.btp_token_url:
            missing.append("BTP_TOKEN_URL")
        if not self.btp_subaccount_id:
            missing.append("BTP_SUBACCOUNT_ID")

        if missing:
            raise ValueError(
                f"\nMissing required environment variables: {', '.join(missing)}\n"
                f"Copy .env.example to .env and fill in your values."
            )


# Single instance — import this everywhere
settings = Settings()