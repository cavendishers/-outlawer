from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.services import curation_service

router = APIRouter()


@router.get("/entities/{entity_id}")
def get_entity_curation_context(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.get_entity_curation_context(db, user_id=user.id, entity_id=entity_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/entities/{entity_id}")
def update_entity(entity_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.update_entity(db, user_id=user.id, entity_id=entity_id, payload=payload))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/entities/{entity_id}/aliases")
def add_entity_alias(entity_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            curation_service.add_entity_alias(
                db,
                user_id=user.id,
                entity_id=entity_id,
                alias=payload.get("alias") or "",
                alias_type=payload.get("alias_type"),
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/entities/{entity_id}/aliases/{alias_id}")
def remove_entity_alias(entity_id: str, alias_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.remove_entity_alias(db, user_id=user.id, entity_id=entity_id, alias_id=alias_id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/entities/{entity_id}/relations")
def upsert_entity_relation(entity_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            curation_service.upsert_entity_relation(
                db,
                user_id=user.id,
                entity_id=entity_id,
                direction=payload.get("direction") or "",
                related_type=payload.get("related_type") or "",
                related_id=payload.get("related_id") or "",
                relation_type=payload.get("relation_type") or "",
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/entities/{entity_id}/relations/{relation_id}")
def update_entity_relation(entity_id: str, relation_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            curation_service.update_entity_relation(
                db,
                user_id=user.id,
                entity_id=entity_id,
                relation_id=relation_id,
                payload=payload,
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/entities/{entity_id}/relations/{relation_id}")
def remove_entity_relation(entity_id: str, relation_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.remove_entity_relation(db, user_id=user.id, entity_id=entity_id, relation_id=relation_id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/events/{event_id}")
def get_event_curation_context(event_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.get_event_curation_context(db, user_id=user.id, event_id=event_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/events/{event_id}")
def update_event(event_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.update_event(db, user_id=user.id, event_id=event_id, payload=payload))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/events/{event_id}/participants")
def upsert_event_participant(event_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            curation_service.upsert_event_participant(
                db,
                user_id=user.id,
                event_id=event_id,
                entity_id=payload.get("entity_id") or "",
                role=payload.get("role"),
                relation_type=payload.get("relation_type"),
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/events/{event_id}/participants/{entity_id}")
def remove_event_participant(event_id: str, entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.remove_event_participant(db, user_id=user.id, event_id=event_id, entity_id=entity_id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/events/{event_id}/relations")
def upsert_event_relation(event_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            curation_service.upsert_event_relation(
                db,
                user_id=user.id,
                event_id=event_id,
                direction=payload.get("direction") or "",
                related_type=payload.get("related_type") or "",
                related_id=payload.get("related_id") or "",
                relation_type=payload.get("relation_type") or "",
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/events/{event_id}/relations/{relation_id}")
def update_event_relation(event_id: str, relation_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            curation_service.update_event_relation(
                db,
                user_id=user.id,
                event_id=event_id,
                relation_id=relation_id,
                payload=payload,
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/events/{event_id}/relations/{relation_id}")
def remove_event_relation(event_id: str, relation_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(curation_service.remove_event_relation(db, user_id=user.id, event_id=event_id, relation_id=relation_id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
