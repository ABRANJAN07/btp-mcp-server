"""
config.py — Reads environment variables from the .env file.

All our settings live here in one place.
The rest of the code imports from this file — never reads os.environ directly.

python-dotenv reads the .env file automatically when we call load_dotenv().
"""

import os
from dotenv import load_dotenv

# Load .env file into environment variables
# This is a no-op if the variables are already set in the environment
load_dotenv()


class Settings:
    """All configuration values in one place."""

    # OAuth2 credentials — from your Service Manager service key
    btp_client_id: str = os.getenv("BTP_CLIENT_ID", "")
    btp_client_secret: str = os.getenv("BTP_CLIENT_SECRET", "")
    btp_token_url: str = os.getenv("BTP_TOKEN_URL", "")

    # Service Manager API base URL — from "sm_url" in your service key
    btp_sm_url: str = os.getenv("BTP_SM_URL", "")

    def validate(self):
        """Check that all required values are set. Fail fast if not."""
        missing = []
        if not self.btp_client_id:
            missing.append("BTP_CLIENT_ID")
        if not self.btp_client_secret:
            missing.append("BTP_CLIENT_SECRET")
        if not self.btp_token_url:
            missing.append("BTP_TOKEN_URL")
        if not self.btp_sm_url:
            missing.append("BTP_SM_URL")

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                f"Copy .env.example to .env and fill in your BTP service key values."
            )


# Create a single instance used everywhere
settings = Settings()