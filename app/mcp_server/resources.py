"""MCP resource descriptors."""


def list_resources() -> list[dict[str, str]]:
    """Return static read-only MCP resource descriptors."""
    return [
        {"uri": "insight://reports/current", "name": "Current report"},
        {"uri": "insight://evidences/current", "name": "Current evidence set"},
    ]
