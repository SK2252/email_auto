"""
config/domains/education.py — Domain Configuration: Education
FERPA + COPPA (where minors involved). Moderate auto-send policy.
"""

DOMAIN_CONFIG = {
    "domain_id":    "education",
    "display_name": "Education",

    "taxonomy": [
        "enrolment_query",
        "fee_payment",
        "academic_record",
        "course_information",
        "student_support",
        "library_access",
        "accommodation_request",
        "complaint",
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
        "Admissions Office",
        "Finance Office",
        "Academic Registry",
        "Student Services",
        "Library Services",
        "Accommodation Office",
    ],

    "routing_rules": {
        "enrolment_query":       "Admissions Office",
        "fee_payment":           "Finance Office",
        "academic_record":       "Academic Registry",
        "course_information":    "Academic Registry",
        "student_support":       "Student Services",
        "library_access":        "Library Services",
        "accommodation_request": "Accommodation Office",
        "complaint":             "Student Services",
    },

    "compliance": {
        "standards":    ["FERPA", "COPPA", "GDPR"],
        "pii_extra":    ["student_id", "GPA", "discipline_record", "disability_record"],
        "pii_extra_patterns": {
            "student_id": r"\bSTU[:\s#]*\d{5,10}\b",
            "GPA":        r"\bGPA[:\s]*[\d]\.\d{1,2}\b",
        },
        "auto_send_allowed":      True,
        "require_audit_sign_off": False,
        "data_retention_days":    1825,  # 5 years post-graduation
    },

    "response_tone": "helpful, encouraging, clear — appropriate for academic context",

    # Academic record, accommodation, complaints always need human review
    "auto_send_types": ["course_information", "library_access", "enrolment_query"],
}
