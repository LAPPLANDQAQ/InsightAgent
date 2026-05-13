"""Structured issue detail helpers."""


def failed_issue_detail(
    *,
    issue_type: str,
    stage: str | None,
    message: str,
) -> dict:
    """Build a structured issue for a failed task."""
    return {
        "type": issue_type,
        "severity": "warning" if issue_type == "cancellation" else "error",
        "stage": stage,
        "message": message,
    }


def structured_issues_from_state(state: dict) -> list[dict]:
    """Build structured issues from workflow state."""
    details = list(state.get("structured_issues") or [])
    severity_map = {"low": "info", "medium": "warning", "high": "error"}
    for issue in state.get("critic_issues") or []:
        severity = str(issue.get("severity") or "warning").lower()
        details.append(
            {
                "type": str(issue.get("issue_type") or "critic"),
                "severity": _normalize_severity(severity, severity_map),
                "stage": issue.get("target_stage"),
                "message": str(issue.get("message") or ""),
            }
        )
    return details


def _normalize_severity(severity: str, severity_map: dict[str, str]) -> str:
    if severity in {"info", "warning", "error"}:
        return severity
    return severity_map.get(severity, "warning")
