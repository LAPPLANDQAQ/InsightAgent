"""Pure deduplication helpers."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.infra.search.base import SearchResult
from app.schemas.evidence import EvidenceItem

TRACKING_PARAMS = {"ref"}


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    Args:
        url: Raw URL.

    Returns:
        URL with lowercase scheme/host, stripped fragment, default ports removed,
        stable query ordering, and removed tracking params.
    """
    parsed = urlsplit(url.strip())
    query_items = [
        (key, value)
        for key, value in sorted(parse_qsl(parsed.query))
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(query_items)
    path = parsed.path.rstrip("/") or "/"
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    if scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]
    return urlunsplit((scheme, netloc, path, query, ""))


def dedupe_search_results(results: list[SearchResult]) -> list[SearchResult]:
    """Deduplicate search results by normalized URL.

    Args:
        results: Search results to deduplicate.

    Returns:
        Results preserving first occurrence order.
    """
    seen: set[str] = set()
    output: list[SearchResult] = []
    for result in results:
        key = normalize_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        output.append(result)
    return output


def dedupe_evidence(evidences: list[EvidenceItem]) -> list[EvidenceItem]:
    """Deduplicate evidence by source, dimension, and claim.

    Args:
        evidences: Evidence items to deduplicate.

    Returns:
        Evidence preserving first occurrence order.
    """
    seen: set[tuple[str, str, str]] = set()
    output: list[EvidenceItem] = []
    for evidence in evidences:
        key = (
            evidence.source_id,
            evidence.dimension.strip().lower(),
            evidence.claim.strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(evidence)
    return output
