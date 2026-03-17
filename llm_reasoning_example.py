"""Example: convert QueryContext into grounded LLMAnswer."""

from __future__ import annotations

from llm import PromptBuilder, ReasoningService
from llm.llm_client import LLMClient
from retrieval.query_models import QueryContext
from vector_store.vector_models import VectorSearchResult

REPO_NAME = "company/carbon-engine"


class MockLLMClient(LLMClient):
    """Deterministic mock client for local reasoning-layer demonstration."""

    def generate(self, prompt: str) -> str:
        _ = prompt
        return (
            "{"
            '"answer": "Emission factor calculation is implemented in CarbonCalculationService.kt '
            "in calculateEmissionFactor(). It is used by ProjectEmissionService and "
            'BuildingFootprintJob, and was introduced in PR #412.", '
            '"sources": ["CarbonCalculationService.kt", "ProjectEmissionService.kt", "PR #412"], '
            '"confidence": 0.92'
            "}"
        )


def main() -> None:
    query_context = QueryContext(
        question="Where is emission factor calculated?",
        retrieved_chunks=[
            VectorSearchResult(
                chunk_id="2f95f6fd-26bb-4f2f-a865-29f6a0ff90af",
                score=0.91,
                text="fun calculateEmissionFactor(materialType: String): Double { ... }",
                metadata={
                    "repo": REPO_NAME,
                    "file_path": "CarbonCalculationService.kt",
                    "source_type": "code_file",
                },
            ),
            VectorSearchResult(
                chunk_id="f324d397-394f-49c7-a2a4-16a9f10d0f8f",
                score=0.84,
                text="ProjectEmissionService invokes calculateEmissionFactor during aggregation.",
                metadata={
                    "repo": REPO_NAME,
                    "file_path": "ProjectEmissionService.kt",
                    "source_type": "code_file",
                },
            ),
            VectorSearchResult(
                chunk_id="3a8f0855-9512-4cf2-a97e-b98cc6f1d51d",
                score=0.79,
                text="PR #412 introduces calculateEmissionFactor and adds usage in BuildingFootprintJob.",
                metadata={
                    "repo": REPO_NAME,
                    "file_path": "PR #412",
                    "source_type": "pull_request",
                },
            ),
        ],
        context_text=(
            "Source: CarbonCalculationService.kt\n"
            "Function: calculateEmissionFactor()\n\n"
            "Source: ProjectEmissionService.kt\n"
            "Uses calculateEmissionFactor() during project aggregation.\n\n"
            "Source: PR #412\n"
            "Introduces calculateEmissionFactor() and BuildingFootprintJob integration."
        ),
    )

    reasoning_service = ReasoningService(
        llm_client=MockLLMClient(),
        prompt_builder=PromptBuilder(),
    )
    answer = reasoning_service.answer_question(query_context)

    print("Answer:")
    print(answer.answer)
    print("\nSources:")
    for source in answer.sources:
        print(f"- {source}")
    print(f"\nConfidence: {answer.confidence:.2f}")


if __name__ == "__main__":
    main()
