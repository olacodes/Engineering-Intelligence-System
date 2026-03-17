"""Prompt construction utilities for LLM reasoning."""

from __future__ import annotations


class PromptBuilder:
    """Builds constrained prompts from question and retrieved context."""

    FALLBACK_ANSWER = (
        "ANSWER\n"
        "Information not present in provided context.\n\n"
        "IMPLEMENTATION\n"
        "Information not present in provided context.\n\n"
        "DEPENDENCIES\n"
        "Information not present in provided context.\n\n"
        "HISTORY\n"
        "Information not present in provided context.\n\n"
        "SOURCES\n"
        "Information not present in provided context."
    )

    def build_prompt(
        self,
        question: str,
        context: str,
        allowed_sources: list[str],
    ) -> str:
        """Construct a strict prompt that limits answers to provided sources."""
        normalized_question = question.strip()
        normalized_context = context.strip()

        if not normalized_question:
            raise ValueError("question cannot be empty")
        if not normalized_context:
            raise ValueError("context cannot be empty")

        rendered_sources = "\n".join(f"- {source}" for source in allowed_sources)
        if not rendered_sources:
            rendered_sources = "- No explicit sources provided"

        return (
            "You are an engineering assistant for a codebase memory system.\n"
            "Use ONLY the provided context and source list.\n"
            "Do not invent files, functions, classes, services, or pull requests.\n"
            "If the answer is not present in the context, state that the information is not present.\n\n"
            "Output must be valid JSON with this schema:\n"
            '{"answer": string, "sources": [string], "confidence": number}\n'
            "- confidence must be between 0 and 1\n"
            "- sources must only include entries from the allowed source list\n\n"
            "The 'answer' value must be plain text (no JSON inside) and use EXACTLY this sectioned format:\n"
            "ANSWER\n"
            "Brief explanation of where the logic exists and how it works.\n\n"
            "IMPLEMENTATION\n"
            "List of relevant files or classes.\n\n"
            "DEPENDENCIES\n"
            "Services or components that use this logic.\n\n"
            "HISTORY\n"
            "Pull request or discussion explaining why the code was introduced.\n"
            "If unavailable, write: Information not present in provided context.\n\n"
            "SOURCES\n"
            "List of files, PRs, or documentation used for the answer.\n"
            "Only cite items from the allowed source list.\n"
            "If unavailable, write: Information not present in provided context.\n\n"
            f"Fallback answer:\n{self.FALLBACK_ANSWER}\n\n"
            f"Question:\n{normalized_question}\n\n"
            f"Allowed sources:\n{rendered_sources}\n\n"
            f"Context:\n{normalized_context}\n"
        )
