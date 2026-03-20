"""
config/domains/hr.py — Domain Configuration: Human Resources
GDPR + local labour law. Sensitive topics — cautious auto-send policy.

GMAIL LABEL ALIGNMENT (config/gmail_labels.json):
  hr / leave / leave_request / grievance / harassment → HR/HR Operations
  payroll / salary_issue / employee_grievance         → HR/Payroll Team
  recruitment / hiring                                → HR/Recruitment Team
  employee_relations / appraisal                      → HR/Employee Relations
  billing / complaint / query / info_request          → Customer Support/Customer Issues
  others                                              → Others/Uncategorised
"""

DOMAIN_CONFIG = {
    "domain_id":    "hr",
    "display_name": "Human Resources",

    # ─────────────────────────────────────────────────────────────────────────
    # HR-specific taxonomy
    # ─────────────────────────────────────────────────────────────────────────
    "taxonomy": [
        "leave_request",
        "payroll_query",
        "benefits_query",
        "onboarding",
        "offboarding",
        "policy_clarification",
        "grievance",
        "recruitment",
        "employee_relations",
        "appraisal",
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # Universal taxonomy — matches gmail_labels.json alias_map keys
    # ─────────────────────────────────────────────────────────────────────────
    "universal_taxonomy": [
        # HR group
        "hr",
        "payroll",
        "recruitment",
        "employee_relations",
        # IT Support group (cross-domain)
        "it",
        "network_issue",
        "security_incident",
        "general_query",
        # Customer Support group (cross-domain)
        "billing",
        "complaint",
        "query",
        "info_request",
        "escalation",
        "product_support",
        "warranty",
        # Catch-all
        "others",
    ],

    # ─────────────────────────────────────────────────────────────────────────
    # SLA rules
    # ─────────────────────────────────────────────────────────────────────────
    "sla_rules": {
        "high":   {"bucket": "4h",  "bucket_seconds": 14400,  "escalate_at": 0.8},
        "medium": {"bucket": "24h", "bucket_seconds": 86400,  "escalate_at": 0.8},
        "low":    {"bucket": "72h", "bucket_seconds": 259200, "escalate_at": 0.8},
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
        # HR group → HR/* labels
        "hr":                  "HR/HR Operations",
        "leave":               "HR/HR Operations",
        "leave_request":       "HR/HR Operations",
        "employee_policy":     "HR/HR Operations",
        "grievance":           "HR/HR Operations",
        "harassment":          "HR/HR Operations",
        "benefits_query":      "HR/HR Operations",
        "policy_clarification":"HR/HR Operations",
        "onboarding":          "HR/HR Operations",
        "payroll":             "HR/Payroll Team",
        "payroll_query":       "HR/Payroll Team",
        "salary_issue":        "HR/Payroll Team",
        "salary":              "HR/Payroll Team",
        "employee_grievance":  "HR/Payroll Team",
        "offboarding":         "HR/Payroll Team",
        "recruitment":         "HR/Recruitment Team",
        "hiring":              "HR/Recruitment Team",
        "employee_relations":  "HR/Employee Relations",
        "appraisal":           "HR/Employee Relations",
        # Cross-domain → Customer Support/* labels
        "billing":             "Customer Support/Customer Issues",
        "complaint":           "Customer Support/Customer Issues",
        "query":               "Customer Support/Customer Issues",
        "info_request":        "Customer Support/Customer Issues",
        "escalation":          "Customer Support/Customer Issues",
        # IT cross-domain
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
        "standards":    ["GDPR", "local_labour_law"],
        "pii_extra":    ["employee_id", "salary", "national_id", "union_membership", "health_condition"],
        "pii_extra_patterns": {
            "employee_id": r"\bEMP[:\s#]*\d{4,8}\b",
            "salary":      r"\b(?:salary|compensation|wage)[:\s]+[\$£€]?[\d,]+(?:\.\d{2})?\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    2555,
    },

    "response_tone": "warm, professional, confidential — HR tone, never legalistic",
    "auto_send_types": ["policy_clarification", "onboarding"],
}