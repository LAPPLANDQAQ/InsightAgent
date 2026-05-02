"""Metric service helpers."""


class MetricService:
    """Compute report metrics."""

    def evidence_count(self, competitors: list[dict]) -> int:
        """Count evidence items.

        Args:
            competitors: Competitor state entries.

        Returns:
            Total evidence count.
        """
        return sum(len(item.get("evidences", [])) for item in competitors)
