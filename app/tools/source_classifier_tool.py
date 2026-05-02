"""Source classification tool."""

from urllib.parse import urlsplit

from app.schemas.source import SourceItem, SourceType

MEDIA_DOMAINS = {"techcrunch.com", "theverge.com", "wired.com", "reuters.com", "bloomberg.com"}
COMMUNITY_DOMAINS = {"reddit.com", "github.com", "stackoverflow.com", "news.ycombinator.com"}
REVIEW_DOMAINS = {"g2.com", "capterra.com", "producthunt.com", "trustpilot.com"}
PAPER_DOMAINS = {"arxiv.org", "doi.org", "acm.org", "ieee.org"}


class SourceClassifierTool:
    """Classify source type and credibility with deterministic rules."""

    def run(
        self,
        *,
        source_id: str,
        url: str,
        title: str,
        retrieved_at: str,
        published_at: str | None = None,
    ) -> SourceItem:
        """Classify a source.

        Args:
            source_id: Source identifier.
            url: Source URL.
            title: Source title.
            retrieved_at: Retrieval timestamp.
            published_at: Optional publication timestamp.

        Returns:
            Validated source item.
        """
        domain = self._domain(url)
        source_type = self._classify(domain)
        return SourceItem(
            source_id=source_id,
            url=url,
            domain=domain,
            title=title,
            source_type=source_type,
            credibility_score=self._score(source_type),
            classification_method="rule",
            published_at=published_at,
            retrieved_at=retrieved_at,
        )

    @staticmethod
    def _domain(url: str) -> str:
        return urlsplit(url).netloc.lower().removeprefix("www.")

    @staticmethod
    def _classify(domain: str) -> SourceType:
        if any(domain.endswith(item) for item in PAPER_DOMAINS):
            return "paper"
        if any(domain.endswith(item) for item in MEDIA_DOMAINS):
            return "media"
        if any(domain.endswith(item) for item in COMMUNITY_DOMAINS):
            return "community"
        if any(domain.endswith(item) for item in REVIEW_DOMAINS):
            return "review"
        if domain:
            return "official"
        return "unknown"

    @staticmethod
    def _score(source_type: SourceType) -> float:
        return {
            "official": 0.9,
            "paper": 0.85,
            "media": 0.75,
            "review": 0.65,
            "community": 0.55,
            "unknown": 0.3,
        }[source_type]
