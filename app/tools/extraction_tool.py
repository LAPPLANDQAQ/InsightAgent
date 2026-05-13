"""Evidence extraction tool."""

import hashlib
import json

from pydantic import BaseModel, Field

from app.infra.cache.base import CacheBackend
from app.infra.llm.base import LLMClient
from app.infra.logger import get_logger
from app.infra.security.redaction import redact_secret_like
from app.schemas.evidence import EvidenceItem
from app.tools.dedup import dedupe_evidence

MAX_EXTRACTION_CHARS = 2000
logger = get_logger(__name__)


class EvidenceExtractionResult(BaseModel):
    """Validated evidence extraction output."""

    evidences: list[EvidenceItem] = Field(default_factory=list)


class ExtractionTool:
    """Extract structured evidence from page text using an LLM."""

    def __init__(self, llm: LLMClient, cache: CacheBackend | None = None) -> None:
        self.llm = llm
        self.cache = cache

    async def run(
        self, *, task_id: str, competitor_name: str, dimension: str,
        source_id: str, source_url: str, text: str, max_evidence: int = 5,
    ) -> EvidenceExtractionResult:
        """Extract validated evidence from a source text.

        Args:
            task_id: Task id used in returned evidence.
            competitor_name: Competitor being researched.
            dimension: Research dimension.
            source_id: Source id.
            source_url: Source URL.
            text: Source text, truncated when longer than 2000 chars.
            max_evidence: Maximum evidence count.

        Returns:
            Validated result.
        """
        prepared_text = self._prepare_text_for_extraction(text)
        cache_key = self._cache_key_for(
            competitor_name,
            dimension,
            source_url,
            prepared_text,
            max_evidence,
        )
        cached_result = await self._cached_result(
            cache_key,
            task_id=task_id,
            competitor_name=competitor_name,
            dimension=dimension,
            source_id=source_id,
            source_url=source_url,
            max_evidence=max_evidence,
        )
        if cached_result is not None:
            return cached_result
        output = await self._extract_uncached(
            task_id=task_id,
            competitor_name=competitor_name,
            dimension=dimension,
            source_id=source_id,
            source_url=source_url,
            text=prepared_text,
            max_evidence=max_evidence,
        )
        if self.cache:
            await self.cache.set(cache_key, output.model_dump_json().encode("utf-8"))
        return output

    @staticmethod
    def _cache_key_for(
        competitor_name: str,
        dimension: str,
        source_url: str,
        text: str,
        max_evidence: int,
    ) -> str:
        return ExtractionTool._cache_key(
            competitor_name=competitor_name,
            dimension=dimension,
            source_url=source_url,
            text=text,
            max_evidence=max_evidence,
        )

    async def _extract_uncached(
        self,
        *,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source_id: str,
        source_url: str,
        text: str,
        max_evidence: int,
    ) -> EvidenceExtractionResult:
        prompt = self._prompt(
            task_id=task_id,
            competitor_name=competitor_name,
            dimension=dimension,
            source_id=source_id,
            source_url=source_url,
            text=text,
            max_evidence=max_evidence,
        )
        result = await self.llm.invoke(
            prompt=prompt,
            model_role="light",
            schema=EvidenceExtractionResult,
            max_tokens=1200,
            temperature=0.1,
        )
        assert not isinstance(result, str)
        evidences = dedupe_evidence(result.evidences)[:max_evidence]
        return EvidenceExtractionResult(evidences=evidences)

    async def _cached_result(
        self,
        cache_key: str,
        *,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source_id: str,
        source_url: str,
        max_evidence: int,
    ) -> EvidenceExtractionResult | None:
        if not self.cache:
            return None
        cached = await self.cache.get(cache_key)
        if cached is None:
            return None
        try:
            cached_result = EvidenceExtractionResult.model_validate_json(cached)
        except Exception as exc:
            logger.exception(
                "extraction_cache_corrupted",
                extra={"cache_key": cache_key, "error": redact_secret_like(str(exc))},
            )
            await self.cache.delete(cache_key)
            return None
        return self._normalize_result(
            cached_result,
            task_id=task_id,
            competitor_name=competitor_name,
            dimension=dimension,
            source_id=source_id,
            source_url=source_url,
            max_evidence=max_evidence,
        )

    @staticmethod
    def _cache_key(
        *,
        competitor_name: str,
        dimension: str,
        source_url: str,
        text: str,
        max_evidence: int,
    ) -> str:
        payload = json.dumps(
            {
                "competitor_name": competitor_name,
                "dimension": dimension,
                "source_url": source_url,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "max_evidence": max_evidence,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return "extract:v2:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _prepare_text_for_extraction(text: str) -> str:
        normalized = " ".join(text.split())
        return normalized[:MAX_EXTRACTION_CHARS]

    @staticmethod
    def _normalize_result(
        result: EvidenceExtractionResult,
        *,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source_id: str,
        source_url: str,
        max_evidence: int,
    ) -> EvidenceExtractionResult:
        evidences = [
            evidence.model_copy(
                update={
                    "task_id": task_id,
                    "competitor_name": competitor_name,
                    "dimension": dimension,
                    "source_id": source_id,
                    "source_url": source_url,
                }
            )
            for evidence in result.evidences
        ]
        return EvidenceExtractionResult(evidences=dedupe_evidence(evidences)[:max_evidence])

    @staticmethod
    def _prompt(
        *,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source_id: str,
        source_url: str,
        text: str,
        max_evidence: int,
    ) -> str:
        return (
            "Extract concise evidence for competitive analysis.\n"
            f"task_id={task_id}\n"
            f"competitor_name={competitor_name}\n"
            f"dimension={dimension}\n"
            f"source_id={source_id}\n"
            f"source_url={source_url}\n"
            f"max_evidence={max_evidence}\n"
            f"text={text}"
        )
