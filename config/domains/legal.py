"""
config/domains/legal.py — Domain Configuration: Legal
Legal privilege applies. Auto-send ALWAYS disabled.
SLA windows are business-day aligned.
"""

DOMAIN_CONFIG = {
    "domain_id":    "legal",
    "display_name": "Legal & Compliance",

    "taxonomy": [
        "contract_review",
        "dispute",
        "regulatory_filing",
        "consultation_request",
        "nda_request",
        "litigation",
        "general_legal_query",
    ],

    "sla_rules": {
        "litigation": {"bucket": "4h",    "bucket_seconds": 14400,  "escalate_at": 0.5},
        "urgent":     {"bucket": "24h",   "bucket_seconds": 86400,  "escalate_at": 0.8},
        "normal":     {"bucket": "72h",   "bucket_seconds": 259200, "escalate_at": 0.8},
        "low":        {"bucket": "7days", "bucket_seconds": 604800, "escalate_at": 0.8},
    },

    "priority_to_sla": {
        "litigation": "litigation",
        "high":       "urgent",
        "medium":     "normal",
        "low":        "low",
    },

    "routing_teams": [
        "Litigation Team",
        "Contract Team",
        "Regulatory Affairs",
        "General Counsel",
        "Compliance Officer",
    ],

    "routing_rules": {
        "contract_review":      "Contract Team",
        "dispute":              "Litigation Team",
        "regulatory_filing":    "Regulatory Affairs",
        "consultation_request": "General Counsel",
        "nda_request":          "Contract Team",
        "litigation":           "Litigation Team",
        "general_legal_query":  "General Counsel",
    },

    "compliance": {
        "standards":    ["legal_privilege", "GDPR", "local_bar_rules"],
        "pii_extra":    ["case_number", "court_reference", "bar_number", "opposing_counsel"],
        "pii_extra_patterns": {
            "case_number": r"\bCase[:\s#]*\d{4,12}\b",
            "court_ref":   r"\b(?:CIVIL|CRIMINAL)[:\s#]*\d{2,8}\b",
        },
        "auto_send_allowed":       False,   # NEVER — legal privilege must be preserved
        "require_audit_sign_off":  True,
        "data_retention_days":     3650,    # 10 years (typical legal records)
    },

    "response_tone": "formal, precise, neutral — never admit liability or make legal statements",

    "auto_send_types": [],
}
