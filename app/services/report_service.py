"""Report service placeholder."""


class ReportService:
    """Service namespace for future report operations."""

    def normalize_markdown(self, markdown: str) -> str:
        """Normalize report Markdown.

        Args:
            markdown: Raw Markdown.

        Returns:
            Trimmed Markdown.
        """
        return markdown.strip()
