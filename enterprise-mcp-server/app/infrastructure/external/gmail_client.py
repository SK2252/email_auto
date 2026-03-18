"""
Gmail API Client — OAuth 2.0 Wrapper with Token Management.

Provides:
  - OAuth 2.0 token load / auto-refresh (5-min buffer before expiry)
  - Exponential backoff retry via tenacity
  - Rate limit tracking
  - PII-sanitized logging

Usage:
    from app.infrastructure.external.gmail_client import get_gmail_service

    service = get_gmail_service(user_id="me")
    messages = service.users().messages().list(userId="me").execute()
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Gmail API scopes — gmail.modify gives read/write/send/labels but NOT delete
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# Paths — driven by app.core.config settings (which reads from .env)
CREDENTIALS_PATH = Path(settings.gmail_credentials_path)
TOKEN_PATH = Path(settings.gmail_token_path)

# Token refresh buffer — refresh if token expires within 5 minutes
TOKEN_REFRESH_BUFFER_SECONDS = 300

# Rate limit tracking
_rate_limit_lock = threading.Lock()
_request_timestamps: list[float] = []
MAX_REQUESTS_PER_SECOND = 50  # Gmail API quota


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class GmailClientError(Exception):
    """Base exception for Gmail client errors."""
    pass


class GmailTokenError(GmailClientError):
    """Raised when OAuth token is missing, expired, or revoked."""
    pass


class GmailRateLimitError(GmailClientError):
    """Raised when Gmail API rate limit is exceeded."""
    pass


class GmailNotConfiguredError(GmailClientError):
    """Raised when Gmail credentials are not set up."""
    pass


# ---------------------------------------------------------------------------
# Token Management
# ---------------------------------------------------------------------------

_cached_credentials: Optional[Credentials] = None
_creds_lock = threading.Lock()


def _load_credentials() -> Credentials:
    """
    Load OAuth credentials from token.json; refresh if near expiry.

    First-time setup:
        Place gmail_credentials.json in the credentials directory,
        then run: python -m app.infrastructure.external.gmail_client
        This will open a browser for OAuth consent and save token.json.
    """
    global _cached_credentials

    with _creds_lock:
        # Return cached if still valid
        if _cached_credentials and _cached_credentials.valid:
            # Check buffer — refresh if expiring within 5 min
            if _cached_credentials.expiry:
                remaining = (_cached_credentials.expiry.timestamp() - time.time())
                if remaining > TOKEN_REFRESH_BUFFER_SECONDS:
                    return _cached_credentials

        creds = None

        # Load from saved token
        if TOKEN_PATH.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), GMAIL_SCOPES)
            except Exception as e:
                logger.warning("Failed to load saved token, will re-authenticate",
                             error=str(e))
                creds = None

        # Refresh expired token
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing Gmail OAuth token")
                creds.refresh(Request())
                _save_token(creds)
                logger.info("Gmail OAuth token refreshed successfully")
            except Exception as e:
                logger.error("Token refresh failed — user must re-authenticate",
                           error=str(e))
                raise GmailTokenError(
                    f"Gmail token refresh failed: {e}. "
                    f"Delete {TOKEN_PATH} and re-authenticate."
                ) from e

        # No valid credentials at all
        if not creds or not creds.valid:
            if not CREDENTIALS_PATH.exists():
                raise GmailNotConfiguredError(
                    f"Gmail not configured. Place your OAuth credentials file at: "
                    f"{CREDENTIALS_PATH}\n"
                    f"Get it from: https://console.cloud.google.com/apis/credentials\n"
                    f"Then run: python -m app.infrastructure.external.gmail_client"
                )

            # Interactive flow — only works during initial setup
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_PATH), GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)
                _save_token(creds)
                logger.info("Gmail OAuth token obtained via browser flow")
            except Exception as e:
                raise GmailTokenError(
                    f"OAuth browser flow failed: {e}. "
                    f"Ensure gmail_credentials.json is valid."
                ) from e

        _cached_credentials = creds
        return creds


def _save_token(creds: Credentials) -> None:
    """Save credentials to token.json for reuse."""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())
    logger.info("Gmail token saved", path=str(TOKEN_PATH))


def invalidate_token() -> None:
    """Force re-authentication on next call (e.g., after revocation)."""
    global _cached_credentials
    with _creds_lock:
        _cached_credentials = None
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
    logger.info("Gmail token invalidated — will re-authenticate on next call")


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

def _check_rate_limit() -> None:
    """Enforce per-second rate limit (50 req/sec for Gmail API)."""
    now = time.time()
    with _rate_limit_lock:
        # Remove timestamps older than 1 second
        _request_timestamps[:] = [
            ts for ts in _request_timestamps if now - ts < 1.0
        ]
        if len(_request_timestamps) >= MAX_REQUESTS_PER_SECOND:
            wait_time = 1.0 - (now - _request_timestamps[0])
            if wait_time > 0:
                logger.warning("Gmail rate limit approached, throttling",
                             wait_seconds=round(wait_time, 2))
                time.sleep(wait_time)
        _request_timestamps.append(time.time())


# ---------------------------------------------------------------------------
# Service Builder
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(HttpError),
    before_sleep=lambda retry_state: logger.warning(
        "Gmail API call failed, retrying",
        attempt=retry_state.attempt_number,
        error=str(retry_state.outcome.exception()) if retry_state.outcome else "unknown",
    ),
)
def get_gmail_service() -> Resource:
    """
    Get an authenticated Gmail API service instance.

    - Auto-refreshes tokens before expiry
    - Retries on transient HttpError (3 attempts with exponential backoff)
    - Thread-safe

    Returns:
        googleapiclient.discovery.Resource — Gmail API service
    """
    _check_rate_limit()
    creds = _load_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    return service


def execute_gmail_api(request_callable) -> Any:
    """
    Execute a Gmail API request with rate limiting, retries, and error handling.

    Usage:
        service = get_gmail_service()
        result = execute_gmail_api(
            service.users().messages().list(userId="me", maxResults=10)
        )

    Args:
        request_callable: A Gmail API request object (from .list(), .get(), etc.)

    Returns:
        API response dict
    """
    _check_rate_limit()

    try:
        result = _execute_with_retry(request_callable)
        return result
    except HttpError as e:
        if e.resp.status == 401:
            logger.error("Gmail auth failed (401) — invalidating token")
            invalidate_token()
            raise GmailTokenError("Gmail authentication failed. Token invalidated.") from e
        elif e.resp.status == 429:
            logger.error("Gmail rate limit exceeded (429)")
            raise GmailRateLimitError("Gmail API rate limit exceeded. Try again later.") from e
        else:
            logger.error("Gmail API error",
                        status=e.resp.status,
                        reason=e.reason if hasattr(e, 'reason') else str(e))
            raise GmailClientError(f"Gmail API error ({e.resp.status}): {e}") from e


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(HttpError),
)
def _execute_with_retry(request_callable) -> Any:
    """Execute a Gmail API request with retries on transient errors."""
    return request_callable.execute()


# ---------------------------------------------------------------------------
# PII Sanitization for Logging
# ---------------------------------------------------------------------------

def sanitize_for_log(text: str) -> str:
    """
    Remove PII patterns from text before logging.
    Masks: email addresses, phone numbers, SSN patterns.
    """
    import re

    # Email addresses
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                  '[EMAIL_REDACTED]', text)
    # US Phone numbers
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                  '[PHONE_REDACTED]', text)
    # SSN
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b',
                  '[SSN_REDACTED]', text)
    return text


# ---------------------------------------------------------------------------
# CLI Entry Point — First-time OAuth setup
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Run this module directly to perform initial OAuth setup:
        python -m app.infrastructure.external.gmail_client

    This opens a browser for Google OAuth consent, then saves the token.
    """
    print("=" * 60)
    print("Gmail OAuth Setup — Enterprise MCP Server")
    print("=" * 60)
    print(f"\nCredentials file: {CREDENTIALS_PATH}")
    print(f"Token will be saved to: {TOKEN_PATH}")
    print()

    if not CREDENTIALS_PATH.exists():
        print(f"ERROR: Credentials file not found at {CREDENTIALS_PATH}")
        print(f"\nTo set up:")
        print(f"  1. Go to https://console.cloud.google.com/apis/credentials")
        print(f"  2. Create OAuth 2.0 Client ID (Desktop Application)")
        print(f"  3. Download the JSON and save it as:")
        print(f"     {CREDENTIALS_PATH}")
        print(f"  4. Run this script again")
        exit(1)

    try:
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        print(f"\n✅ Success! Authenticated as: {profile.get('emailAddress')}")
        print(f"   Total messages: {profile.get('messagesTotal')}")
        print(f"   Token saved to: {TOKEN_PATH}")
    except Exception as e:
        print(f"\n❌ Failed: {e}")
        exit(1)
