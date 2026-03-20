"""
config/domains/it_support.py — Domain Configuration: IT Support
ISO27001 / SOC2. Auto-send allowed for simple ticket types.

FIX: Added universal_taxonomy — when this domain is used as the DEFAULT
inbox (receives ALL email types, not just IT), the LLM needs the full
category set to correctly classify billing, HR, complaints etc.
Without this, non-IT emails fall through to general_query incorrectly.
"""

DOMAIN_CONFIG = {
    "domain_id":    "it_support",
    "display_name": "IT Support",

    # -----------------------------------------------------------------------
    # IT-specific taxonomy — used when domain is explicitly set to it_support
    # -----------------------------------------------------------------------
    "taxonomy": [
        "password_reset",
        "hardware_issue",
        "software_bug",
        "access_request",
        "network_issue",
        "onboarding",
        "security_incident",
        "general_query",
    ],

    # -----------------------------------------------------------------------
    # universal_taxonomy — reserved for future multi-domain inbox use.
    # To activate: pass universal_taxonomy to build_classification_prompts()
    # -----------------------------------------------------------------------
    # "universal_taxonomy": [
    #     "password_reset",
    #     "hardware_issue",
    #     "software_bug",
    #     "access_request",
    #     "network_issue",
    #     "onboarding",
    #     "security_incident",
    #     "billing",
    #     "hr",
    #     "complaint",
    #     "query",
    #     "info_request",
    #     "escalation",
    #     "general_query",
    #     "other",
    # ],

    "sla_rules": {
        "security_incident": {"bucket": "30min", "bucket_seconds": 1800,   "escalate_at": 0.5},
        "high":              {"bucket": "4h",    "bucket_seconds": 14400,  "escalate_at": 0.8},
        "medium":            {"bucket": "8h",    "bucket_seconds": 28800,  "escalate_at": 0.8},
        "low":               {"bucket": "24h",   "bucket_seconds": 86400,  "escalate_at": 0.8},
    },

    "priority_to_sla": {
        "security_incident": "security_incident",
        "high":              "high",
        "medium":            "medium",
        "low":               "low",
    },

    "routing_teams": [
        "Tier 1 Support",
        "Tier 2 Engineering",
        "Security Team",
        "Network Ops",
        "IT Onboarding",
    ],

    "routing_rules": {
        "password_reset":    "IT Support/General IT Queue",
        "hardware_issue":    "IT Support/General IT Queue",
        "software_bug":      "IT Support/General IT Queue",
        "access_request":    "IT Support/Security Team",
        "network_issue":     "IT Support/Network Ops Team",
        "onboarding":        "HR/Recruitment Team",
        "security_incident": "IT Support/Security Team",
        "general_query":     "IT Support/General IT Queue",
    },

    "compliance": {
        "standards":    ["ISO27001", "SOC2"],
        "pii_extra":    ["employee_id", "device_serial", "ip_address"],
        "pii_extra_patterns": {
            "employee_id":   r"\bEMP[:\s#]*\d{4,8}\b",
            "device_serial": r"\bSN[:\s#]*[A-Z0-9]{8,20}\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    365,
    },

    "response_tone": "technical, concise, solution-focused — avoid jargon",

    "auto_send_types": ["password_reset", "general_query"],
}
