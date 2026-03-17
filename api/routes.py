"""FastAPI routes for EIS query endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .api_models import AskRequest, AskResponse
from .dependencies import get_query_controller
from .query_controller import QueryController

router = APIRouter(tags=["Query API"])


@router.post("/ask", response_model=AskResponse, summary="Ask engineering question")
async def ask(
    request: AskRequest,
    controller: QueryController = Depends(get_query_controller),
) -> AskResponse:
    """Execute retrieval + reasoning pipeline and return structured answer."""
    return await controller.ask_question(request)
