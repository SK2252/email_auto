"""
Enterprise MCP Server — Configuration
Loads all settings from environment variables via pydantic-settings.
"""

import json
import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All application settings loaded from environment variables."""

    # --- Server ---
    mcp_server_host: str = "0.0.0.0"
    mcp_tools_port: int = 9000
    opn_agent_port: int = 8001
    environment: str = "development"
    debug: bool = False

    # --- Logging ---
    log_level: str = "INFO"
    log_format: str = "json"
    log_output: str = "stdout"

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # --- PostgreSQL ---
    database_url: str = "postgresql+asyncpg://postgres:yakkay-321@localhost:5433/postgres"
    #database_url: str = "postgresql+asyncpg://mcp_user:password@localhost:5432/mcp_server"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_recycle: int = 1800

    # --- OPN-Agent Paths ---
    opn_agent_base_dir: str = "D:/email_auto/src/OPN-Agent"
    opn_data_input_dir: str = "D:/email_auto/src/OPN-Agent/AI_open_negotiation/Data/Input"
    opn_data_output_dir: str = "D:/email_auto/src/OPN-Agent/AI_open_negotiation/Data/Output"

    # --- Filesystem MCP Server ---
    filesystem_allowed_dirs: List[str] = [
        "D:/email_auto/src/OPN-Agent/AI_open_negotiation/Data"
    ]

    @field_validator("filesystem_allowed_dirs", mode="before")
    @classmethod
    def parse_allowed_dirs(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [d.strip() for d in v.split(",")]
        return v

    # --- Session Management ---
    session_ttl_seconds: int = 3600
    session_max_refreshes: int = 3
    session_absolute_timeout_seconds: int = 14400
    session_max_per_key: int = 5

    # --- Rate Limiting ---
    rate_limit_default: str = "100/minute"
    rate_limit_mcp: str = "60/minute"

    # --- Security ---
    api_key_header: str = "X-API-Key"
    hmac_signing_enabled: bool = False
    hmac_timestamp_tolerance_seconds: int = 300

    # --- Compliance ---
    audit_retention_days: int = 2555  # 7 years
    audit_local_log_dir: str = "logs/audit"

    # --- Gmail API ---
    gmail_credentials_path: str = "D:/email_auto/credentials/gmail_credentials.json"
    gmail_token_path: str = "D:/email_auto/credentials/gmail_token.json"

    # --- Microsoft Graph API (Outlook) ---
    microsoft_graph_client_id: str = ""
    microsoft_graph_client_secret: str = ""
    microsoft_graph_tenant_id: str = "common"

    # --- LLM / Grok API ---
    grok_api_key: str = ""
    grok_model: str = "llama-3.3-70b-versatile"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def log_level_upper(self) -> str:
        return self.log_level.upper()

    model_config = {
        "env_file": "D:/email_auto/.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


# Singleton instance — import this everywhere
settings = Settings()
