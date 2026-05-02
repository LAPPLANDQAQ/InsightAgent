"""Evidence extraction tool."""

from pydantic import BaseModel, Field

from app.infra.llm.base import LLMClient
from app.schemas.evidence import EvidenceItem
from app.tools.dedup import dedupe_evidence


class EvidenceExtractionResult(BaseModel):
    """Validated evidence extraction output."""

    evidences: list[EvidenceItem] = Field(default_factory=list)


class ExtractionTool:
    """Extract structured evidence from page text using an LLM."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    async def run(
        self,
        *,
        task_id: str,
        competitor_name: str,
        dimension: str,
        source_id: str,
        source_url: str,
        text: str,
        max_evidence: int = 5,
    ) -> EvidenceExtractionResult:
        """Extract evidence from text.

        Args:
            task_id: Task identifier.
            competitor_name: Competitor name.
            dimension: Research dimension.
            source_id: Source identifier.
            source_url: Source URL.
            text: Page text. Values longer than 2000 characters are rejected.
            max_evidence: Maximum evidence items to return.

        Returns:
            Validated extraction result.

        Raises:
            ValueError: Raised when text exceeds the maximum extraction size.
        """
        if len(text) > 2000:
            raise ValueError("Extraction input exceeds 2000 characters")
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
        evidences = dedupe_evidence(result.evidences)[:max_evidence]
        return EvidenceExtractionResult(evidences=evidences)

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
