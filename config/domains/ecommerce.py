"""
config/domains/ecommerce.py — Domain Configuration: E-Commerce
GDPR + consumer protection law. High auto-send safe for order queries.
"""

DOMAIN_CONFIG = {
    "domain_id":    "ecommerce",
    "display_name": "E-Commerce",

    "taxonomy": [
        "order_status",
        "return_request",
        "refund_request",
        "delivery_issue",
        "product_query",
        "account_issue",
        "discount_query",
        "complaint",
        "fraud_report",
    ],

    "sla_rules": {
        "fraud":   {"bucket": "1h",  "bucket_seconds": 3600,  "escalate_at": 0.5},
        "urgent":  {"bucket": "4h",  "bucket_seconds": 14400, "escalate_at": 0.8},
        "normal":  {"bucket": "24h", "bucket_seconds": 86400, "escalate_at": 0.8},
        "low":     {"bucket": "48h", "bucket_seconds": 172800,"escalate_at": 0.8},
    },

    "priority_to_sla": {
        "fraud_report": "fraud",
        "high":   "urgent",
        "medium": "normal",
        "low":    "low",
    },

    "routing_teams": [
        "Customer Service",
        "Fulfilment Ops",
        "Returns & Refunds",
        "Fraud Prevention",
        "Technical Support",
    ],

    "routing_rules": {
        "order_status":   "Customer Service",
        "return_request": "Returns & Refunds",
        "refund_request": "Returns & Refunds",
        "delivery_issue": "Fulfilment Ops",
        "product_query":  "Customer Service",
        "account_issue":  "Technical Support",
        "discount_query": "Customer Service",
        "complaint":      "Customer Service",
        "fraud_report":   "Fraud Prevention",
    },

    "compliance": {
        "standards":    ["GDPR", "consumer_protection", "DSA"],
        "pii_extra":    ["order_id", "payment_method", "delivery_address"],
        "pii_extra_patterns": {
            "order_id": r"\bORD[:\s#]*[A-Z0-9]{6,12}\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    730,  # 2 years for consumer records
    },

    "response_tone": "friendly, upbeat, solution-focused — mirror the brand voice",

    "auto_send_types": ["order_status", "product_query", "discount_query"],
}
