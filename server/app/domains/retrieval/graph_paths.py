from __future__ import annotations

from collections import deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity, EventEntity, Relation
from app.models.event import Event


NodeKey = tuple[str, str]


def find_graph_path(
    db: Session,
    *,
    user_id: str,
    source_type: str,
    source_id: str,
    target_type: str,
    target_id: str,
    max_depth: int = 4,
) -> dict[str, Any]:
    if source_type not in {"event", "entity"} or target_type not in {"event", "entity"}:
        raise ValueError("Graph paths support event and entity nodes only")
    if max_depth < 1 or max_depth > 6:
        raise ValueError("max_depth must be between 1 and 6")

    events = db.scalars(select(Event).where(Event.user_id == user_id)).all()
    entities = db.scalars(select(Entity).where(Entity.user_id == user_id)).all()
    nodes: dict[NodeKey, dict[str, str]] = {
        ("event", row.id): graph_path_node("event", row.id, row.title) for row in events
    }
    nodes.update(
        {("entity", row.id): graph_path_node("entity", row.id, row.display_name) for row in entities}
    )
    source_key = (source_type, source_id)
    target_key = (target_type, target_id)
    if source_key not in nodes or target_key not in nodes:
        raise ValueError("Graph path endpoint not found")

    graph_edges: list[dict[str, Any]] = []
    participant_rows = db.scalars(
        select(EventEntity)
        .join(Event, Event.id == EventEntity.event_id)
        .join(Entity, Entity.id == EventEntity.entity_id)
        .where(Event.user_id == user_id, Entity.user_id == user_id)
    ).all()
    for row in participant_rows:
        label = row.relation_type or row.role or "participates_in"
        graph_edges.append(
            {
                "source_type": "entity",
                "source_id": row.entity_id,
                "target_type": "event",
                "target_id": row.event_id,
                "label": label,
                "fact_type": "participation",
                "relation_id": None,
                "evidence_count": 0,
                "confidence": row.confidence_score,
                "detail": row.role,
            }
        )

    relations = db.scalars(
        select(Relation).where(
            Relation.user_id == user_id,
            Relation.source_type.in_(["event", "entity"]),
            Relation.target_type.in_(["event", "entity"]),
        )
    ).all()
    for row in relations:
        graph_edges.append(
            {
                "source_type": row.source_type,
                "source_id": row.source_id,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "label": row.relation_type,
                "fact_type": "relation",
                "relation_id": row.id,
                "evidence_count": row.evidence_count,
                "confidence": row.confidence_score,
                "detail": None,
            }
        )

    adjacency: dict[NodeKey, list[tuple[NodeKey, dict[str, Any], bool]]] = {}
    for edge in graph_edges:
        edge_source = (edge["source_type"], edge["source_id"])
        edge_target = (edge["target_type"], edge["target_id"])
        if edge_source not in nodes or edge_target not in nodes:
            continue
        adjacency.setdefault(edge_source, []).append((edge_target, edge, True))
        adjacency.setdefault(edge_target, []).append((edge_source, edge, False))

    queue: deque[tuple[NodeKey, int]] = deque([(source_key, 0)])
    previous: dict[NodeKey, tuple[NodeKey, dict[str, Any], bool] | None] = {source_key: None}
    while queue:
        current, depth = queue.popleft()
        if current == target_key:
            break
        if depth >= max_depth:
            continue
        for neighbor, edge, forward in adjacency.get(current, []):
            if neighbor in previous:
                continue
            previous[neighbor] = (current, edge, forward)
            queue.append((neighbor, depth + 1))

    if target_key not in previous:
        return {
            "found": False,
            "max_depth": max_depth,
            "total_hops": 0,
            "source": nodes[source_key],
            "target": nodes[target_key],
            "nodes": [nodes[source_key], nodes[target_key]],
            "edges": [],
            "explanation": f"在 {max_depth} 跳范围内没有找到连接路径。",
        }

    path_keys: list[NodeKey] = []
    path_steps: list[tuple[NodeKey, NodeKey, dict[str, Any], bool]] = []
    cursor = target_key
    while cursor != source_key:
        path_keys.append(cursor)
        previous_step = previous[cursor]
        if previous_step is None:
            break
        parent, edge, forward = previous_step
        path_steps.append((parent, cursor, edge, forward))
        cursor = parent
    path_keys.append(source_key)
    path_keys.reverse()
    path_steps.reverse()

    serialized_edges = [
        serialize_path_edge(nodes, parent, child, edge, forward)
        for parent, child, edge, forward in path_steps
    ]
    labels = [nodes[key]["label"] for key in path_keys]
    return {
        "found": True,
        "max_depth": max_depth,
        "total_hops": len(serialized_edges),
        "source": nodes[source_key],
        "target": nodes[target_key],
        "nodes": [nodes[key] for key in path_keys],
        "edges": serialized_edges,
        "explanation": f"找到 {len(serialized_edges)} 跳路径：{' → '.join(labels)}",
    }


def graph_path_node(node_type: str, node_id: str, label: str) -> dict[str, str]:
    return {
        "id": node_id,
        "node_type": node_type,
        "label": label,
        "href": f"/graph?{'event_id' if node_type == 'event' else 'entity_id'}={node_id}&active_node_id={node_id}",
    }


def serialize_path_edge(
    nodes: dict[NodeKey, dict[str, str]],
    traversal_source: NodeKey,
    traversal_target: NodeKey,
    edge: dict[str, Any],
    forward: bool,
) -> dict[str, Any]:
    source_label = nodes[traversal_source]["label"]
    target_label = nodes[traversal_target]["label"]
    direction = "forward" if forward else "reverse"
    direction_word = "指向" if forward else "反向关联到"
    evidence = f"，{edge['evidence_count']} 条证据" if edge.get("evidence_count") else ""
    confidence = (
        f"，置信度 {float(edge['confidence']):.2f}" if edge.get("confidence") is not None else ""
    )
    return {
        "source_type": traversal_source[0],
        "source_id": traversal_source[1],
        "target_type": traversal_target[0],
        "target_id": traversal_target[1],
        "label": edge["label"],
        "fact_type": edge["fact_type"],
        "relation_id": edge.get("relation_id"),
        "evidence_count": int(edge.get("evidence_count") or 0),
        "confidence": edge.get("confidence"),
        "traversal_direction": direction,
        "explanation": f"{source_label} 通过“{edge['label']}”{direction_word} {target_label}{evidence}{confidence}。",
    }
