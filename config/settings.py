"""
config/settings.py — Centralised Configuration
All secrets, model strings, thresholds, and API base URLs live here.
Agents NEVER hardcode provider or model names.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # -----------------------------------------------------------------------
    # LLM Providers (ZERO BUDGET — free tiers only)
    # -----------------------------------------------------------------------
    # Groq — AG-02 Classification, Sentiment, PII confirmation
    GROQ_API_KEY:       str = ""
    GROQ_BASE_URL:      str = "https://api.groq.com/openai/v1"
    GROQ_MODEL:         str = "llama-3.3-70b-versatile"
    GROQ_RPM_LIMIT:     int = 30           # requests per minute (free tier)
    GROQ_RPD_LIMIT:     int = 14_400       # requests per day

    # Google AI Studio — AG-03 Routing fallback, AG-04 Response drafting
    GOOGLE_API_KEY:     str = ""
    GEMINI_MODEL:       str = "gemini-2.5-flash-lite"
    GEMINI_RPD_LIMIT:   int = 1_000        # requests per day (free tier)

    # Mistral AI — AG-07 Analytics insights
    MISTRAL_API_KEY:    str = ""
    MISTRAL_BASE_URL:   str = "https://api.mistral.ai/v1"
    MISTRAL_MODEL:      str = "mistral-small-latest"

    # -----------------------------------------------------------------------
    # Gmail — OAuth 2.0 (SETUP COMPLETE, do not regenerate auth code)
    # -----------------------------------------------------------------------
    GMAIL_CLIENT_ID:        Optional[str] = None
    GMAIL_CLIENT_SECRET:    Optional[str] = None
    GMAIL_REFRESH_TOKEN:    Optional[str] = None   # stored after initial OAuth dance
    GMAIL_REDIRECT_URI:     str = "http://localhost:8080"

    # -----------------------------------------------------------------------
    # Microsoft Graph — Auth IN PROGRESS
    # -----------------------------------------------------------------------
    GRAPH_CLIENT_ID:        Optional[str] = None
    GRAPH_CLIENT_SECRET:    Optional[str] = None
    GRAPH_TENANT_ID:        Optional[str] = None
    GRAPH_USER_EMAIL:       Optional[str] = None   # mailbox to poll

    # -----------------------------------------------------------------------
    # Zendesk
    # -----------------------------------------------------------------------
    ZENDESK_SUBDOMAIN:  Optional[str] = None
    ZENDESK_EMAIL:      Optional[str] = None
    ZENDESK_API_TOKEN:  Optional[str] = None

    # -----------------------------------------------------------------------
    # Freshdesk
    # -----------------------------------------------------------------------
    FRESHDESK_DOMAIN:   Optional[str] = None
    FRESHDESK_API_KEY:  Optional[str] = None

    # -----------------------------------------------------------------------
    # ServiceNow — AG-03 Routing (OAuth 2.0)
    # -----------------------------------------------------------------------
    SERVICENOW_INSTANCE_URL:    Optional[str] = None   # e.g. https://myco.service-now.com
    SERVICENOW_CLIENT_ID:       Optional[str] = None
    SERVICENOW_CLIENT_SECRET:   Optional[str] = None
    # Legacy basic-auth fallback (kept for compatibility)
    SERVICENOW_INSTANCE:        Optional[str] = None
    SERVICENOW_USER:            Optional[str] = None
    SERVICENOW_PASS:            Optional[str] = None

    # -----------------------------------------------------------------------
    # Jira — AG-03 Routing (API Token)
    # -----------------------------------------------------------------------
    JIRA_SITE_URL:      Optional[str] = None   # e.g. https://yourco.atlassian.net
    JIRA_USER:          Optional[str] = None
    JIRA_API_TOKEN:     Optional[str] = None
    # Legacy alias
    JIRA_URL:           Optional[str] = None

    # -----------------------------------------------------------------------
    # Salesforce (CRM)
    # -----------------------------------------------------------------------
    SALESFORCE_CLIENT_ID:       Optional[str] = None
    SALESFORCE_CLIENT_SECRET:   Optional[str] = None
    SALESFORCE_USERNAME:        Optional[str] = None

    # -----------------------------------------------------------------------
    # HubSpot (CRM fallback)
    # -----------------------------------------------------------------------
    HUBSPOT_API_KEY:    Optional[str] = None

    # -----------------------------------------------------------------------
    # Slack — alerts, escalations, SLA notifications
    # -----------------------------------------------------------------------
    SLACK_BOT_TOKEN:            Optional[str] = None   # xoxb- token for slack-mcp
    SLACK_WEBHOOK_URL:          Optional[str] = None   # legacy incoming webhook
    SLACK_TEAM_LEAD_CHANNEL:    str = "#escalations"
    SLACK_COMPLIANCE_CHANNEL:   str = "#compliance-alerts"
    SLACK_SLA_CHANNEL:          str = "#sla-alerts"
    # Channel IDs (preferred over names for slack-mcp)
    SLACK_CHANNEL_ESCALATIONS:  str = "#escalations"
    SLACK_CHANNEL_SLA_ALERTS:   str = "#sla-alerts"
    SLACK_CHANNEL_COMPLIANCE:   str = "#compliance-alerts"
    SLACK_CHANNEL_ANALYTICS:    str = "#analytics"
    SLACK_TEAM_LEAD_USER_ID:    Optional[str] = None  # User ID for DM alerts

    # Email fallback for when Slack alert fails
    TEAM_LEAD_EMAIL:            Optional[str] = None

    # -----------------------------------------------------------------------
    # Celery & Redis
    # -----------------------------------------------------------------------
    CELERY_BROKER_URL:          str = "redis://localhost:6379/0"

    # -----------------------------------------------------------------------
    # PostgreSQL
    # -----------------------------------------------------------------------
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/inbox_mgmt"

    # -----------------------------------------------------------------------
    # Application — thresholds (LOCKED from design doc, do not change)
    # -----------------------------------------------------------------------
    CONFIDENCE_THRESHOLD:           float = 0.7    # below → human review
    SENTIMENT_ESCALATION_THRESHOLD: float = -0.5   # below → Slack alert to Team Lead
    GEMINI_CACHE_TTL_SECONDS:       int   = 3_600  # response cache TTL for AG-04
    ROUTING_LLM_FALLBACK_RETRIES:   int   = 2      # AG-03 Gemini fallback: 2x ONLY
    ROUTING_TIMEOUT_SECONDS:        int   = 15     # AG-03 must complete within 15s

    # -----------------------------------------------------------------------
    # Polling & SLA
    # -----------------------------------------------------------------------
    POLLING_INTERVAL_SECONDS:   int = 5
    SLA_BUCKET_4H_SECONDS:      int = 4  * 3600
    SLA_BUCKET_24H_SECONDS:     int = 24 * 3600
    SLA_BUCKET_48H_SECONDS:     int = 48 * 3600
    SLA_ALERT_THRESHOLD_PCT:    float = 0.80   # alert when 80% of SLA elapsed

    # -----------------------------------------------------------------------
    # Storage
    # -----------------------------------------------------------------------
    ATTACHMENT_STORAGE_PATH: str = "./attachments"


# Singleton instance
settings = Settings()
