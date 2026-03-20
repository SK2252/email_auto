"""
config/domains/billing.py — Domain Configuration: Billing & Finance
PCI-DSS / GDPR. Auto-send allowed for confirmations only.

GMAIL LABEL ALIGNMENT (config/gmail_labels.json):
  billing / complaint / query / info_request → Customer Support/Customer Issues
  product_support / product_issue            → Customer Support/Product Support
  warranty / warranty_claim                  → Customer Support/Warranty
  hr / payroll / recruitment                 → HR/* labels (cross-domain)
  it / network_issue / security_incident     → IT Support/* labels (cross-domain)
  others                                     → Others/Uncategorised
"""

DOMAIN_CONFIG = {
    "domain_id":    "billing",
    "display_name": "Billing & Finance",

    # ─────────────────────────────────────────────────────────────────────────
    # Billing-specific taxonomy
    # ─────────────────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────────────────
    # Universal taxonomy — matches gmail_labels.json alias_map keys
    # ─────────────────────────────────────────────────────────────────────────
    "universal_taxonomy": [
        # Customer Support group
        "billing",
        "complaint",
        "query",
        "info_request",
        "escalation",
        "product_support",
        "warranty",
        # HR cross-domain
        "hr",
        "payroll",
        "recruitment",
        "employee_relations",
        # IT cross-domain
        "it",
        "network_issue",
        "security_incident",
        "general_query",
        # Catch-all
        "others",
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # SLA rules
    # ─────────────────────────────────────────────────────────────────────────
    "sla_rules": {
        "high":   {"bucket": "4h",  "bucket_seconds": 14400, "escalate_at": 0.8},
        "medium": {"bucket": "8h",  "bucket_seconds": 28800, "escalate_at": 0.8},
        "low":    {"bucket": "24h", "bucket_seconds": 86400, "escalate_at": 0.8},
    },

    "priority_to_sla": {
        "high":   "high",
        "medium": "medium",
        "low":    "low",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Routing rules — category → Gmail sub-label path (matches alias_map)
    # ─────────────────────────────────────────────────────────────────────────
    "routing_rules": {
        # Customer Support group → Customer Support/* labels
        "billing":             "Customer Support/Customer Issues",
        "invoice_dispute":     "Customer Support/Customer Issues",
        "payment_failure":     "Customer Support/Customer Issues",
        "refund_request":      "Customer Support/Customer Issues",
        "overcharge":          "Customer Support/Customer Issues",
        "subscription_change": "Customer Support/Customer Issues",
        "tax_query":           "Customer Support/Customer Issues",
        "general_billing":     "Customer Support/Customer Issues",
        "payment_confirmation":"Customer Support/Customer Issues",
        "complaint":           "Customer Support/Customer Issues",
        "query":               "Customer Support/Customer Issues",
        "info_request":        "Customer Support/Customer Issues",
        "escalation":          "Customer Support/Customer Issues",
        "customer_support":    "Customer Support/Customer Issues",
        "product_support":     "Customer Support/Product Support",
        "product_issue":       "Customer Support/Product Support",
        "product_query":       "Customer Support/Product Support",
        "warranty":            "Customer Support/Warranty",
        "warranty_claim":      "Customer Support/Warranty",
        # HR cross-domain → HR/* labels
        "hr":                  "HR/HR Operations",
        "payroll":             "HR/Payroll Team",
        "recruitment":         "HR/Recruitment Team",
        "employee_relations":  "HR/Employee Relations",
        # IT cross-domain → IT Support/* labels
        "it":                  "IT Support/IT Support Team",
        "network_issue":       "IT Support/Network Ops Team",
        "security_incident":   "IT Support/Security Team",
        "general_query":       "IT Support/General IT Queue",
        # Catch-all
        "others":              "Others/Uncategorised",
        "other":               "Others/Uncategorised",
        "unknown":             "Others/Uncategorised",
    },

    # ─────────────────────────────────────────────────────────────────────────
    # Compliance
    # ─────────────────────────────────────────────────────────────────────────
    "compliance": {
        "standards":    ["PCI_DSS", "GDPR"],
        "pii_extra":    ["card_number", "bank_account", "sort_code", "IBAN", "CVV"],
        "pii_extra_patterns": {
            "card_number": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
            "sort_code":   r"\b\d{2}-\d{2}-\d{2}\b",
            "cvv":         r"\bCVV[:\s#]*\d{3,4}\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    2555,
    },

    "response_tone": "professional, precise, reassuring — never dismissive about money concerns",
    "auto_send_types": ["payment_confirmation", "general_billing"],
}