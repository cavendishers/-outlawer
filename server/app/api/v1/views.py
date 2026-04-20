from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models.style_view import StyleView
from app.schemas.common import Envelope
from app.schemas.view import StoryViewResponse

router = APIRouter()


@router.get("/story/note/{note_id}", response_model=Envelope[StoryViewResponse])
def note_story(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    story = db.scalar(
        select(StyleView).where(
            StyleView.user_id == user.id,
            StyleView.target_type == "note",
            StyleView.target_id == note_id,
        )
    )
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story view not found")
    return {"code": 0, "message": "ok", "data": story_to_dict(story)}


@router.get("/story/entity/{entity_id}", response_model=Envelope[StoryViewResponse])
def entity_story(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    story = db.scalar(
        select(StyleView).where(
            StyleView.user_id == user.id,
            StyleView.target_type == "entity",
            StyleView.target_id == entity_id,
        )
    )
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story view not found")
    return {"code": 0, "message": "ok", "data": story_to_dict(story)}


def story_to_dict(story: StyleView) -> dict:
    return {
        "id": story.id,
        "target_type": story.target_type,
        "target_id": story.target_id,
        "title": story.title,
        "content": story.content,
        "style_type": story.style_type,
    }
