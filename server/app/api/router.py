from fastapi import APIRouter

from app.api.v1 import (
    assets,
    auth,
    character_cards,
    curation,
    entities,
    events,
    graph,
    health,
    image_generations,
    jobs,
    notes,
    operations,
    review,
    search,
    timeline,
    views,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(character_cards.router, prefix="/character-cards", tags=["character-cards"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(entities.router, prefix="/entities", tags=["entities"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(curation.router, prefix="/curation", tags=["curation"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
api_router.include_router(views.router, prefix="/views", tags=["views"])
api_router.include_router(graph.router, prefix="/graph", tags=["graph"])
api_router.include_router(image_generations.router, prefix="/image-generations", tags=["image-generations"])
