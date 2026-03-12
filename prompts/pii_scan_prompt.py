"""
prompts/pii_scan_prompt.py — PROMPT-05 (Domain-Aware)
Layer 2 LLM semantic PII detection prompt (used inside utils/pii_scanner.py).
Provider: Groq llama-3.3-70b-versatile.

DYNAMIC: domain-specific PII types are injected at runtime from domain_config.
"""


def build_pii_scan_prompts(domain_config: dict | None = None) -> tuple[str, str]:
    """
    Build domain-aware system + user prompt strings for the PII scanner LLM layer.

    Args:
        domain_config: Optional loaded domain config. If None, uses generic baseline.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    # Base PII types always checked
    base_pii_types = (
        "full names with addresses, passport numbers, medical records, "
        "bank account details, driver's licence numbers, biometric data, "
        "tax file numbers, employee IDs combined with names"
    )

    # Domain-specific additions
    extra_types = ""
    if domain_config:
        extra = domain_config.get("compliance", {}).get("pii_extra", [])
        domain_name = domain_config.get("display_name", "")
        if extra:
            extra_types = (
                f"\n\nAdditional PII types specific to {domain_name}:\n"
                + ", ".join(extra)
            )

    system_prompt = f"""
You are a PII (Personally Identifiable Information) detection specialist.
Detect any PII in the provided text that regex patterns may have missed.

PII types to find: {base_pii_types}{extra_types}

Output ONLY valid JSON:
{{"pii_detected": <true|false>, "reason": "<short explanation or 'none'>"}}

DO NOT output anything outside the JSON object.
Err on the side of caution: if unsure, set pii_detected to true.
""".strip()

    user_prompt = "Detect PII in the following text:\n\n{text}"

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Backwards-compatible constants
# ---------------------------------------------------------------------------
PII_SCAN_SYSTEM_PROMPT = """
You are a PII (Personally Identifiable Information) detection specialist.
Detect any PII in the provided text that regex patterns may have missed.

PII types to find: full names with addresses, passport numbers, 
medical records, bank account details, driver's licence numbers, 
biometric data, tax file numbers, employee IDs combined with names.

Output ONLY valid JSON:
{"pii_detected": <true|false>, "reason": "<short explanation or 'none'>"}

DO NOT output anything outside the JSON object.
Err on the side of caution: if unsure, set pii_detected to true.
""".strip()

PII_SCAN_USER_PROMPT = "Detect PII in the following text:\n\n{text}"
