"""
config/domains/billing.py — Domain Configuration: Billing & Finance
PCI-DSS / GDPR. Auto-send allowed for confirmations only.
"""

DOMAIN_CONFIG = {
    "domain_id":    "billing",
    "display_name": "Billing & Finance",

    "taxonomy": [
        "invoice_dispute",
        "payment_failure",
        "refund_request",
        "subscription_change",
        "tax_query",
        "overcharge",
        "payment_confirmation",
        "general_billing",
    ],

    "sla_rules": {
        "dispute": {"bucket": "4h",  "bucket_seconds": 14400, "escalate_at": 0.8},
        "refund":  {"bucket": "8h",  "bucket_seconds": 28800, "escalate_at": 0.8},
        "query":   {"bucket": "24h", "bucket_seconds": 86400, "escalate_at": 0.8},
    },

    "priority_to_sla": {
        "high":   "dispute",
        "medium": "refund",
        "low":    "query",
    },

    "routing_teams": [
        "Finance Ops",
        "Refunds Team",
        "Disputes Team",
        "Accounts Receivable",
        "Tax & Compliance",
    ],

    "routing_rules": {
        "invoice_dispute":    "Disputes Team",
        "payment_failure":    "Finance Ops",
        "refund_request":     "Refunds Team",
        "subscription_change":"Accounts Receivable",
        "tax_query":          "Tax & Compliance",
        "overcharge":         "Disputes Team",
        "payment_confirmation":"Finance Ops",
        "general_billing":    "Finance Ops",
    },

    "compliance": {
        "standards":    ["PCI_DSS", "GDPR"],
        "pii_extra":    ["card_number", "bank_account", "sort_code", "IBAN", "CVV"],
        "pii_extra_patterns": {
            "card_number":  r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "sort_code":    r"\b\d{2}-\d{2}-\d{2}\b",
            "cvv":          r"\bCVV[:\s#]*\d{3,4}\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    2555,    # 7 years for financial records
    },

    "response_tone": "professional, precise, reassuring — never dismissive about money concerns",

    "auto_send_types": ["payment_confirmation", "general_billing"],
}
