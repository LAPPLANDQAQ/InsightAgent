"""MCP prompt descriptors."""


def list_prompts() -> list[dict[str, str]]:
    """Return static MCP prompt descriptors."""
    return [
        {
            "name": "summarize_report",
            "description": "Summarize the current evidence-grounded research report.",
        }
    ]
