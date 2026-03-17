"""Controller orchestrating query API request flow."""

from __future__ import annotations

import time

from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from llm.llm_client import ClaudeAPIError
from llm.llm_models import LLMAnswer
from llm.reasoning_service import ReasoningService
from retrieval.query_models import QueryRequest
from retrieval.retrieval_service import RetrievalService

from utils.logger import get_logger

from .api_models import AskRequest, AskResponse

logger = get_logger(__name__)


class QueryController:
    """Coordinates retrieval and reasoning for incoming API queries."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        reasoning_service: ReasoningService,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._reasoning_service = reasoning_service

    async def ask_question(self, request: AskRequest) -> AskResponse:
        """Process one query request and return structured answer payload."""
        started = time.perf_counter()
        logger.info("Received query request (top_k=%d)", request.top_k)

        query_request = QueryRequest(question=request.question, top_k=request.top_k)

        try:
            query_context = await run_in_threadpool(
                self._retrieval_service.build_context,
                query_request,
            )
            llm_answer: LLMAnswer = await run_in_threadpool(
                self._reasoning_service.answer_question,
                query_context,
            )
        except HTTPException:
            raise
        except ClaudeAPIError as exc:
            logger.exception("LLM upstream request failed: %s", exc)
            raise HTTPException(
                status_code=502,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("Query pipeline failed: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="Failed to process question through EIS query pipeline.",
            ) from exc

        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "Query completed in %.2fms with %d sources",
            latency_ms,
            len(llm_answer.sources),
        )

        return AskResponse(
            answer=llm_answer.answer,
            sources=llm_answer.sources,
            confidence=llm_answer.confidence,
        )
