import argparse
from uuid import uuid4

import httpx
from sqlalchemy import delete, or_, select

from app.core.database import SessionLocal
from app.models.collection import KnowledgeCollection, KnowledgeCollectionItem
from app.models.entity import Entity, EntityAlias, EventEntity, Relation
from app.models.event import Event, TimelineItem
from app.models.manual_knowledge import ManualKnowledgeEvidence
from app.models.note import Note
from app.models.raw_asset import RawAsset
from app.models.review import ReviewAction
from app.models.user import User


def assert_ok(response: httpx.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    assert payload["code"] == 0, payload
    return payload["data"]


def seed_source(username: str) -> tuple[str, str]:
    marker = uuid4().hex[:8]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username))
        assert user is not None
        asset = RawAsset(user_id=user.id, asset_type="text", source_type="manual", title=f"Manual E2E Asset {marker}", original_text="张三主持了专题会议。", status="uploaded")
        db.add(asset)
        db.flush()
        note = Note(user_id=user.id, asset_id=asset.id, title=f"Manual E2E Note {marker}", canonical_text=asset.original_text, status="ready")
        db.add(note)
        db.commit()
        return asset.id, note.id


def cleanup(ids: dict[str, str]) -> None:
    with SessionLocal() as db:
        collection_id = ids.get("collection_id")
        event_id = ids.get("event_id")
        entity_id = ids.get("entity_id")
        note_id = ids.get("note_id")
        asset_id = ids.get("asset_id")
        if collection_id:
            db.execute(delete(KnowledgeCollectionItem).where(KnowledgeCollectionItem.collection_id == collection_id))
            db.execute(delete(KnowledgeCollection).where(KnowledgeCollection.id == collection_id))
        target_ids = {value for key, value in ids.items() if key.endswith("_id") and value}
        if target_ids:
            db.execute(delete(ReviewAction).where(ReviewAction.target_id.in_(target_ids)))
        if entity_id or event_id:
            conditions = []
            if entity_id:
                conditions.append(ManualKnowledgeEvidence.target_id == entity_id)
            if event_id:
                conditions.append(ManualKnowledgeEvidence.target_id == event_id)
            db.execute(delete(ManualKnowledgeEvidence).where(or_(*conditions)))
        if event_id:
            db.execute(delete(EventEntity).where(EventEntity.event_id == event_id))
            db.execute(delete(TimelineItem).where(TimelineItem.event_id == event_id))
        if entity_id:
            db.execute(delete(EventEntity).where(EventEntity.entity_id == entity_id))
            db.execute(delete(EntityAlias).where(EntityAlias.entity_id == entity_id))
        if event_id or entity_id:
            relation_conditions = []
            if event_id:
                relation_conditions.extend([Relation.source_id == event_id, Relation.target_id == event_id])
            if entity_id:
                relation_conditions.extend([Relation.source_id == entity_id, Relation.target_id == entity_id])
            db.execute(delete(Relation).where(or_(*relation_conditions)))
        if event_id:
            db.execute(delete(Event).where(Event.id == event_id))
        if entity_id:
            db.execute(delete(Entity).where(Entity.id == entity_id))
        if note_id:
            db.execute(delete(Note).where(Note.id == note_id))
        if asset_id:
            db.execute(delete(RawAsset).where(RawAsset.id == asset_id))
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123456")
    args = parser.parse_args()
    ids: dict[str, str] = {}
    try:
        ids["asset_id"], ids["note_id"] = seed_source(args.username)
        client = httpx.Client(timeout=20.0, trust_env=False)
        login = assert_ok(client.post(f"{args.base_url}/auth/login", json={"username": args.username, "password": args.password}))
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        marker = uuid4().hex[:8]

        entity_result = assert_ok(
            client.post(
                f"{args.base_url}/entities",
                headers=headers,
                json={
                    "canonical_name": f"手工人物-{marker}",
                    "entity_type": "person",
                    "description": "由 Phase 31 e2e 创建",
                    "evidence": {"note_id": ids["note_id"], "excerpt": "张三主持了专题会议"},
                },
            )
        )
        ids["entity_id"] = entity_result["entity"]["id"]
        assert entity_result["evidence"]["note_id"] == ids["note_id"]

        graph_result = assert_ok(
            client.post(
                f"{args.base_url}/graph/manual-nodes",
                headers=headers,
                json={
                    "node_type": "event",
                    "name": f"手工事件-{marker}",
                    "subtype": "meeting",
                    "anchor_type": "entity",
                    "anchor_id": ids["entity_id"],
                    "relation_type": "hosts",
                    "role": "主持人",
                    "event_time": "2026-07-11T10:00:00+08:00",
                },
            )
        )
        ids["event_id"] = graph_result["node_id"]
        ids["connection_id"] = graph_result["connection_id"]
        assert graph_result["connection_type"] == "participant"

        collection = assert_ok(
            client.post(
                f"{args.base_url}/collections",
                headers=headers,
                json={"title": f"专题案件-{marker}", "description": "Phase 32/33 e2e", "collection_type": "case"},
            )
        )
        ids["collection_id"] = collection["id"]
        candidates = assert_ok(
            client.get(
                f"{args.base_url}/collections/{ids['collection_id']}/candidates",
                headers=headers,
                params={"item_type": "entity", "q": f"手工人物-{marker}"},
            )
        )
        assert candidates["total"] == 1 and candidates["items"][0]["item_id"] == ids["entity_id"]
        collection_item_ids: list[str] = []
        for item_type, item_id in (("note", ids["note_id"]), ("entity", ids["entity_id"]), ("event", ids["event_id"])):
            item = assert_ok(client.post(f"{args.base_url}/collections/{ids['collection_id']}/items", headers=headers, json={"item_type": item_type, "item_id": item_id, "curator_note": f"收录 {item_type}"}))
            collection_item_ids.append(item["id"])

        detail = assert_ok(client.get(f"{args.base_url}/collections/{ids['collection_id']}", headers=headers))
        assert detail["item_count"] == 3
        assert detail["stats"]["by_type"] == {"note": 1, "entity": 1, "event": 1}
        assert detail["stats"]["evidence_coverage"] == 0.5
        evidence = assert_ok(client.get(f"{args.base_url}/manual-knowledge/evidence", headers=headers, params={"target_type": "entity", "target_id": ids["entity_id"]}))
        assert evidence["total"] == 1 and evidence["items"][0]["note_id"] == ids["note_id"]
        reordered = assert_ok(client.put(f"{args.base_url}/collections/{ids['collection_id']}/items/order", headers=headers, json={"item_ids": list(reversed(collection_item_ids))}))
        assert reordered["item_ids"][0] == collection_item_ids[-1]
        collection_graph = assert_ok(client.get(f"{args.base_url}/graph/workspace", headers=headers, params={"collection_id": ids["collection_id"]}))
        assert collection_graph["scope"] == "collection"
        assert {item["id"] for item in collection_graph["nodes"]} == {ids["entity_id"], ids["event_id"]}
        timeline = assert_ok(client.get(f"{args.base_url}/collections/{ids['collection_id']}/timeline", headers=headers))
        assert timeline["items"][0]["event_id"] == ids["event_id"]
        story = assert_ok(client.post(f"{args.base_url}/collections/{ids['collection_id']}/story/compile", headers=headers))
        assert "关键材料与人物" in story["body"]
        markdown = assert_ok(client.get(f"{args.base_url}/collections/{ids['collection_id']}/export?format=markdown", headers=headers))
        json_export = assert_ok(client.get(f"{args.base_url}/collections/{ids['collection_id']}/export?format=json", headers=headers))
        assert markdown["filename"].endswith(".md") and "收录对象" in markdown["content"]
        assert json_export["filename"].endswith(".json") and '"timeline"' in json_export["content"]
        removed = assert_ok(client.post(f"{args.base_url}/collections/{ids['collection_id']}/items/bulk-remove", headers=headers, json={"item_ids": [collection_item_ids[0]]}))
        assert removed["removed_ids"] == [collection_item_ids[0]]
        print("Manual authoring, collection, timeline, story, and export e2e flow passed.")
    finally:
        cleanup(ids)


if __name__ == "__main__":
    main()
