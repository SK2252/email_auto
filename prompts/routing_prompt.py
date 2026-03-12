"""
prompts/routing_prompt.py — PROMPT-03 (Domain-Aware)
AI routing fallback for AG-03 when rule-based matrix has no clear match.
Uses Gemini 2.5 Flash-Lite (via llm_client.py).

DYNAMIC: routing teams and categories are injected at runtime from domain_config.
"""


def build_routing_prompts(domain_config: dict) -> tuple[str, str]:
    """
    Build domain-aware system + user prompt strings for AG-03.

    Args:
        domain_config: Loaded domain config from utils/domain_loader.py.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    domain_name = domain_config.get("display_name", "customer support")
    routing_teams = domain_config.get("routing_teams", [])
    routing_rules = domain_config.get("routing_rules", {})

    # Build a human-readable routing table for the LLM
    routing_table_lines = []
    for category, team in routing_rules.items():
        routing_table_lines.append(f"  {category} → {team}")
    routing_table = "\n".join(routing_table_lines)

    teams_list = ", ".join(routing_teams)

    system_prompt = f"""
You are an intelligent email routing specialist for a {domain_name} inbox.

Your job: assign an inbound email to the most appropriate team.

Available teams for {domain_name}:
  {teams_list}

Default routing rules (use as guidance, not rigid rules):
{routing_table}

Output ONLY valid JSON:
{{
  "routing_decision": "<team_name from the list above>",
  "confidence":       <float 0.0–1.0>,
  "reason":           "<one sentence justification>"
}}

RULES:
  - routing_decision MUST be one of the available teams listed above.
  - Never invent a team name not in the list.
  - If no rule matches, use your best judgment.

DO NOT include text outside the JSON object.
""".strip()

    user_prompt = """
Email classification result:
{classification_json}

Determine the best team assignment from the available teams.
""".strip()

    return system_prompt, user_prompt


# ---------------------------------------------------------------------------
# Backwards-compatible constants
# ---------------------------------------------------------------------------
ROUTING_SYSTEM_PROMPT = """
You are an intelligent email routing specialist.
Given a classified email and available team routing options, determine the best team assignment.

Output ONLY valid JSON:
{
  "routing_decision": "<team_name>",
  "confidence":       <float 0.0–1.0>,
  "reason":           "<one sentence justification>"
}

DO NOT include text outside the JSON object.
""".strip()

ROUTING_USER_PROMPT = """
Email classification:
{classification_json}

Available teams and their responsibility:
{routing_matrix_json}

Determine the best team assignment.
""".strip()
