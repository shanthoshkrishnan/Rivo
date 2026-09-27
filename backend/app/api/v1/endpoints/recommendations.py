"""
RIVO Backend — Recommendations API Endpoint
=============================================
POST /api/v1/recommendations/search

The main RIVO Home endpoint.  Runs the full pipeline:
  hard constraints → spatial filter → facility filter →
  route evaluation (max 200 listings) → scoring → ranking.

Every result includes:
  - Affordability breakdown (rent + maintenance + transport)
  - Best route per preferred mode
  - Family facility access (school / hospital / pharmacy)
  - Explainability block (why_recommended — data driven, no LLM)
  - Confidence level (HIGH / MEDIUM / LOW)
  - Data freshness label

This endpoint NEVER returns a blank page — loading states are
managed by the frontend while awaiting this response.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.recommendation import (
    RecommendationDetailRequest,
    RecommendationDetailResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.providers.registry import (
    get_places_provider,
    get_rental_provider,
    get_route_provider,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "/search",
    response_model=RecommendationResponse,
    summary="Find suitable homes",
    description=(
        "Run the full RIVO Home pipeline: "
        "hard constraint filtering → spatial filter → route evaluation → "
        "affordability scoring → explainable recommendations. "
        "At most 200 listings are routed per request."
    ),
)
async def recommendations_search(
    request: RecommendationRequest,
    db: AsyncSession | None = Depends(get_db),
) -> RecommendationResponse:
    service = RecommendationService(
        rental_provider=get_rental_provider(),
        route_provider=get_route_provider(),
        places_provider=get_places_provider(),
        db=db,
    )
    return await service.search(request)


@router.post(
    "/detail",
    response_model=RecommendationDetailResponse,
    summary="Get detailed live travel & family plan for a selected home",
    description=(
        "Run deep live evaluation for a single selected home: "
        "multimodal transit itinerary, multi-mode road comparison, live family facilities, "
        "and truthful data provenance."
    ),
)
async def recommendations_detail(
    request: RecommendationDetailRequest,
    db: AsyncSession | None = Depends(get_db),
) -> RecommendationDetailResponse:
    service = RecommendationService(
        rental_provider=get_rental_provider(),
        route_provider=get_route_provider(),
        places_provider=get_places_provider(),
        db=db,
    )
    return await service.detail(request)

