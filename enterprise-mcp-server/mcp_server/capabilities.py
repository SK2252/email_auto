"""
MCP Server capability declarations.

get_instructions() returns the server instruction string to be passed
directly into the FastMCP constructor in main.py.
FastMCP does not support setting instructions as a post-init property.
"""


def get_instructions() -> str:
    """
    Return server instructions shown to agents at connection time.
    Pass the return value to FastMCP(..., instructions=get_instructions()).
    """
    return (
        "Enterprise MCP Server v2.0. "
        "Provides 31 tools across 4 domains: "
        "email (19 Gmail tools), document (5 OPN workflow tools), "
        "filesystem (5 secure file tools), jobs (2 background job tools). "
        "All tools use dependency injection via lifespan context. "
        "ISO 42001:2023 AI governance compliant."
    )
