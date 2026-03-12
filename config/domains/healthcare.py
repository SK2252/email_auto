"""
config/domains/healthcare.py — Domain Configuration: Healthcare
HIPAA / HITECH compliant. Auto-send is ALWAYS disabled.
"""

DOMAIN_CONFIG = {
    "domain_id":    "healthcare",
    "display_name": "Healthcare",

    # -----------------------------------------------------------------------
    # Email taxonomy — replaces hardcoded inquiry|complaint|... in PROMPT-01
    # -----------------------------------------------------------------------
    "taxonomy": [
        "appointment",
        "prescription_refill",
        "lab_result",
        "insurance_query",
        "emergency",
        "billing",
        "medical_record_request",
        "complaint",
    ],

    # -----------------------------------------------------------------------
    # SLA rules — bucket + escalation threshold (fraction of deadline elapsed)
    # -----------------------------------------------------------------------
    "sla_rules": {
        "emergency":  {"bucket": "15min", "bucket_seconds": 900,    "escalate_at": 0.5},
        "urgent":     {"bucket": "1h",    "bucket_seconds": 3600,   "escalate_at": 0.8},
        "normal":     {"bucket": "4h",    "bucket_seconds": 14400,  "escalate_at": 0.8},
        "low":        {"bucket": "24h",   "bucket_seconds": 86400,  "escalate_at": 0.8},
    },

    # -----------------------------------------------------------------------
    # Priority → SLA tier mapping
    # -----------------------------------------------------------------------
    "priority_to_sla": {
        "emergency": "emergency",
        "high":      "urgent",
        "medium":    "normal",
        "low":       "low",
    },

    # -----------------------------------------------------------------------
    # Routing teams — replaces Finance Ops / IT Support / HR Ops etc.
    # -----------------------------------------------------------------------
    "routing_teams": [
        "Triage Nurse",
        "Billing Dept",
        "Appointments Desk",
        "Pharmacy",
        "Medical Records",
        "Insurance Coordinator",
    ],

    # -----------------------------------------------------------------------
    # Category → default team mapping (rule-based fast path in AG-03)
    # -----------------------------------------------------------------------
    "routing_rules": {
        "appointment":            "Appointments Desk",
        "prescription_refill":    "Pharmacy",
        "lab_result":             "Triage Nurse",
        "insurance_query":        "Insurance Coordinator",
        "emergency":              "Triage Nurse",
        "billing":                "Billing Dept",
        "medical_record_request": "Medical Records",
        "complaint":              "Triage Nurse",
    },

    # -----------------------------------------------------------------------
    # Compliance & PII
    # -----------------------------------------------------------------------
    "compliance": {
        "standards":    ["HIPAA", "HITECH"],
        "pii_extra":    [
            "MRN",              # Medical Record Number
            "NPI",              # National Provider Identifier
            "ICD10_code",       # Diagnosis codes
            "prescription_id",  # Rx identifiers
            "diagnosis",        # Diagnosis text
            "PHI",              # Protected Health Information (catch-all)
        ],
        "pii_extra_patterns": {
            "MRN":          r"\bMRN[:\s#]*\d{6,10}\b",
            "NPI":          r"\bNPI[:\s#]*\d{10}\b",
            "ICD10":        r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b",    # e.g. Z23.4
            "prescription": r"\bRx[:\s#]*\d{6,12}\b",
        },
        "auto_send_allowed":       False,   # NEVER auto-send in healthcare
        "require_audit_sign_off":  True,
        "data_retention_days":     2555,    # 7 years (HIPAA requirement)
    },

    # -----------------------------------------------------------------------
    # Response tone injected into PROMPT-04
    # -----------------------------------------------------------------------
    "response_tone": "empathetic, clinical, reassuring — never alarmist",

    # -----------------------------------------------------------------------
    # Auto-send override type list (ignored since auto_send_allowed=False)
    # -----------------------------------------------------------------------
    "auto_send_types": [],
}
