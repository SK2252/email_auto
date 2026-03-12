"""
config/domains/hr.py — Domain Configuration: Human Resources
GDPR + local labour law. Sensitive topics → cautious auto-send policy.
"""

DOMAIN_CONFIG = {
    "domain_id":    "hr",
    "display_name": "Human Resources",

    "taxonomy": [
        "leave_request",
        "payroll_query",
        "benefits_query",
        "onboarding",
        "offboarding",
        "policy_clarification",
        "grievance",
        "recruitment",
    ],

    "sla_rules": {
        "urgent": {"bucket": "4h",  "bucket_seconds": 14400, "escalate_at": 0.8},
        "normal": {"bucket": "24h", "bucket_seconds": 86400, "escalate_at": 0.8},
        "low":    {"bucket": "72h", "bucket_seconds": 259200,"escalate_at": 0.8},
    },

    "priority_to_sla": {
        "high":   "urgent",
        "medium": "normal",
        "low":    "low",
    },

    "routing_teams": [
        "HR Generalist",
        "Payroll Team",
        "Benefits Administrator",
        "Talent Acquisition",
        "HR Business Partner",
        "Employee Relations",
    ],

    "routing_rules": {
        "leave_request":      "HR Generalist",
        "payroll_query":      "Payroll Team",
        "benefits_query":     "Benefits Administrator",
        "onboarding":         "HR Generalist",
        "offboarding":        "HR Business Partner",
        "policy_clarification":"HR Generalist",
        "grievance":          "Employee Relations",
        "recruitment":        "Talent Acquisition",
    },

    "compliance": {
        "standards":    ["GDPR", "local_labour_law"],
        "pii_extra":    ["employee_id", "salary", "national_id", "union_membership", "health_condition"],
        "pii_extra_patterns": {
            "employee_id": r"\bEMP[:\s#]*\d{4,8}\b",
            "salary":      r"\b(?:salary|compensation|wage)[:\s]+[\$£€]?[\d,]+(?:\.\d{2})?\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    2555,  # 7 years (typical HR legal requirement)
    },

    "response_tone": "warm, professional, confidential — HR tone, never legalistic",

    # Only generic acknowledgements auto-send, never payroll/grievance/offboarding
    "auto_send_types": ["policy_clarification", "onboarding"],
}
