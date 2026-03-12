"""
prompts/classification_prompt.py — PROMPT-01 (Domain-Aware)
Single batched prompt for BOTH classification AND sentiment scoring.
One Groq API call = conserves 30 rpm free quota.

DYNAMIC: taxonomy and SLA buckets are injected at runtime from domain_config.
Agents call build_classification_prompts(domain_config) instead of importing
the string constants directly.
"""


def build_classification_prompts(domain_config: dict) -> tuple[str, str]:
    """
    Build domain-aware system + user prompt strings for AG-02.

    Args:
        domain_config: Loaded domain config from utils/domain_loader.py.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    taxonomy        = " | ".join(domain_config.get("taxonomy", ["inquiry", "complaint", "other"]))
    sla_buckets     = " | ".join(domain_config.get("sla_rules", {}).keys())
    domain_name     = domain_config.get("display_name", "customer support")
    priority_levels = list(domain_config.get("sla_rules", {}).keys())

    # Build priority guidance from the domain's own SLA rules
    priority_guidance_lines = []
    for tier, rule in domain_config.get("sla_rules", {}).items():
        bucket = rule.get("bucket", "24h")
        priority_guidance_lines.append(f"  - {tier:20s} / {bucket}")
    priority_guidance = "\n".join(priority_guidance_lines) if priority_guidance_lines else (
        "  - high   / 4h\n  - medium / 24h\n  - low    / 48h"
    )

    system_prompt = f"""
You are an expert email triage AI for a {domain_name} inbox management system.

Your task is to classify the email AND assess its sentiment in ONE response.

Classify into EXACTLY one of these domain-specific categories:
  <{taxonomy}>

Output ONLY a valid JSON object with exactly these keys:
{{
  "category":        "<{taxonomy}>",
  "priority":        "<{" | ".join(priority_levels)}>",
  "sla_bucket":      "<{sla_buckets}>",
  "confidence":      <float 0.0–1.0>,
  "sentiment_score": <float -1.0 to 1.0>
}}

Priority and SLA rules for {domain_name}:
{priority_guidance}

Confidence: your certainty that the category is correct (not the sentiment).
Sentiment: -1.0 = very angry/urgent, 0.0 = neutral, 1.0 = very positive.

DO NOT include any text outside the JSON object.
DO NOT invent categories outside the list above.
""".strip()

    user_prompt = """
Classify the following customer email:

---
{email_text}
---
""".strip()

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Backwards-compatible constants (used by existing classification_agent.py
# before domain-awareness refactor; kept so imports don't break immediately).
# Agents should migrate to build_classification_prompts(domain_config).
# ---------------------------------------------------------------------------
CLASSIFICATION_SYSTEM_PROMPT = """
You are an expert email triage AI for a customer support inbox management system.

Your task is to classify the email AND assess its sentiment in ONE response.

Output ONLY a valid JSON object with exactly these keys:
{
  "category":       "<inquiry | complaint | technical_issue | billing | spam | other>",
  "priority":       "<high | medium | low>",
  "sla_bucket":     "<4h | 24h | 48h>",
  "confidence":     <float 0.0–1.0>,
  "sentiment_score": <float -1.0 to 1.0>
}

Priority and SLA rules:
  - high   / 4h:  service outage, data loss, legal threat, billing dispute > $1000
  - medium / 24h: technical problem, complaint, refund request
  - low    / 48h: general inquiry, feedback, feature request, spam

Confidence: your certainty that the category is correct (not the sentiment).
Sentiment: -1.0 = very angry/urgent, 0.0 = neutral, 1.0 = very positive.

DO NOT include any text outside the JSON object.
""".strip()

CLASSIFICATION_USER_PROMPT = """
Classify the following customer email:

---
{email_text}
---
""".strip()
