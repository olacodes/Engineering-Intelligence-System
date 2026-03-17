"""Example: convert ingestion output (KnowledgeItem) into retrieval chunks."""

from __future__ import annotations

from models.knowledge_models import KnowledgeItem, SourceType
from chunking.chunk_service import ChunkService


def build_sample_items() -> list[KnowledgeItem]:
    """Create representative items from different source types."""
    code_item = KnowledgeItem(
        source_type=SourceType.CODE_FILE,
        repo="core-engine",
        file_path="services/carbon/CarbonCalculationService.kt",
        content=(
            "class CarbonCalculationService {\n"
            "    fun calculateEmissionFactor(distanceKm: Double): Double {\n"
            "        return distanceKm * 0.21\n"
            "    }\n\n"
            "    fun calculateTripEmission(distanceKm: Double, passengers: Int): Double {\n"
            "        val factor = calculateEmissionFactor(distanceKm)\n"
            "        return factor / passengers\n"
            "    }\n"
            "}\n"
        ),
    )

    pr_item = KnowledgeItem(
        source_type=SourceType.PULL_REQUEST,
        repo="core-engine",
        file_path="pull_requests/421",
        content=(
            "# Add carbon optimization cache\n\n"
            "Introduces an in-memory cache for repeated carbon computations.\n\n"
            "Comments:\n"
            "- Great improvement, but please add cache invalidation docs.\n"
            "- Can we include hit/miss metrics in telemetry?\n"
        ),
    )

    doc_item = KnowledgeItem(
        source_type=SourceType.DOCUMENTATION,
        repo="core-engine",
        file_path="docs/emissions.md",
        content=(
            "# Emission Pipeline\n\n"
            "The emission pipeline computes distance-based factors.\n\n"
            "## Inputs\n\n"
            "- Distance in kilometers\n"
            "- Transport mode\n\n"
            "## Outputs\n\n"
            "- Estimated CO2e\n"
            "- Confidence score\n"
        ),
    )

    return [code_item, pr_item, doc_item]


def main() -> None:
    items = build_sample_items()
    chunk_service = ChunkService()
    chunks = chunk_service.chunk_items(items)

    print(f"Input items: {len(items)}")
    print(f"Generated chunks: {len(chunks)}")
    print("-" * 80)

    for idx, chunk in enumerate(chunks, start=1):
        preview = chunk.text.replace("\n", " ")[:100]
        print(
            f"[{idx}] parent={chunk.parent_id} source={chunk.metadata['source_type']}"
        )
        print(f"    file={chunk.metadata['file_path']}")
        print(f"    preview={preview}...")


if __name__ == "__main__":
    main()
