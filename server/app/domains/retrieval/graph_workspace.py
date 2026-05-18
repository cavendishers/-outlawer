from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.retrieval import entity_query, event_query, timeline_query
from app.models.review import ReviewAction


@dataclass(frozen=True)
class GraphWorkspaceFilters:
    node_types: set[str]
    relation_types: set[str]
    start: datetime | None = None
    end: datetime | None = None
    min_weight: float = 0.0
    depth: int = 0


def parse_filter_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def parse_datetime_filter(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_graph_filters(
    *,
    node_types: str | None = None,
    relation_types: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_weight: float | None = None,
    depth: int | None = None,
) -> GraphWorkspaceFilters:
    return GraphWorkspaceFilters(
        node_types={item for item in parse_filter_csv(node_types) if item in {"event", "entity"}},
        relation_types=parse_filter_csv(relation_types),
        start=parse_datetime_filter(start),
        end=parse_datetime_filter(end),
        min_weight=max(0.0, min(float(min_weight or 0.0), 1.0)),
        depth=max(0, min(int(depth or 0), 2)),
    )


def get_graph_workspace(
    db: Session,
    *,
    user_id: str,
    event_id: str | None = None,
    entity_id: str | None = None,
    node_types: str | None = None,
    relation_types: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_weight: float | None = None,
    depth: int | None = None,
) -> dict[str, Any]:
    filters = normalize_graph_filters(
        node_types=node_types,
        relation_types=relation_types,
        start=start,
        end=end,
        min_weight=min_weight,
        depth=depth,
    )
    if event_id:
        return finalize_workspace(db, apply_workspace_filters(build_event_workspace(db, user_id=user_id, event_id=event_id), filters), user_id=user_id)
    if entity_id:
        return finalize_workspace(db, apply_workspace_filters(build_entity_workspace(db, user_id=user_id, entity_id=entity_id), filters), user_id=user_id)
    return finalize_workspace(db, apply_workspace_filters(build_overview_workspace(db, user_id=user_id), filters), user_id=user_id)


def get_graph_node_detail(
    db: Session,
    *,
    user_id: str,
    node_type: str,
    node_id: str,
    event_id: str | None = None,
    entity_id: str | None = None,
    node_types: str | None = None,
    relation_types: str | None = None,
    start: str | None = None,
    end: str | None = None,
    min_weight: float | None = None,
    depth: int | None = None,
) -> dict[str, Any]:
    workspace = get_graph_workspace(
        db,
        user_id=user_id,
        event_id=event_id if event_id else (node_id if node_type == "event" and not entity_id else None),
        entity_id=entity_id if entity_id else (node_id if node_type == "entity" and not event_id else None),
        node_types=node_types,
        relation_types=relation_types,
        start=start,
        end=end,
        min_weight=min_weight,
        depth=depth,
    )
    node = next(
        (
            item
            for item in workspace["nodes"]
            if item["id"] == node_id and item["node_type"] == node_type
        ),
        None,
    )
    if node is None:
        raise ValueError("Graph node not found")

    connected_edges = [
        edge
        for edge in workspace["edges"]
        if edge["source_id"] == node_id or edge["target_id"] == node_id
    ]
    connected_node_ids = []
    relation_label_map: dict[str, str] = {}
    for edge in connected_edges:
        peer_id = edge["target_id"] if edge["source_id"] == node_id else edge["source_id"]
        if peer_id not in connected_node_ids:
            connected_node_ids.append(peer_id)
        relation_label_map[peer_id] = edge["label"]

    connected_nodes = []
    for item in workspace["nodes"]:
        if item["id"] not in connected_node_ids:
            continue
        connected_nodes.append(
            {
                "id": item["id"],
                "node_type": item["node_type"],
                "label": item["label"],
                "subtitle": item["subtitle"],
                "href": item["href"],
                "meta": item.get("meta", []),
                "relation_label": relation_label_map.get(item["id"]),
                "is_anchor": item.get("is_anchor", False),
            }
        )

    timeline_context = build_timeline_context_for_node(
        node=node,
        workspace=workspace,
        connected_nodes=connected_nodes,
    )

    anchor_actions = [action("回到总览", "/graph", "anchor_overview", "secondary")]
    if node_type == "event":
        anchor_actions.append(action("以此事件为锚点", f"/graph?event_id={node_id}", "anchor_event", "primary"))
    elif node_type == "entity":
        anchor_actions.append(action("以此人物为锚点", f"/graph?entity_id={node_id}", "anchor_entity", "primary"))

    current_anchor = workspace.get("anchor")
    if current_anchor and current_anchor["id"] != node_id:
        if current_anchor["node_type"] == "event":
            href = f"/graph?event_id={current_anchor['id']}"
        elif current_anchor["node_type"] == "entity":
            href = f"/graph?entity_id={current_anchor['id']}"
        else:
            href = "/graph"
        anchor_actions.append(
            action(f"返回锚点：{current_anchor['label']}", href, "anchor_current", "info")
        )

    return {
        "node": node,
        "connected_nodes": connected_nodes,
        "connected_edges": connected_edges,
        "timeline_context": timeline_context,
        "anchor_actions": anchor_actions,
    }


def apply_workspace_filters(workspace: dict[str, Any], filters: GraphWorkspaceFilters) -> dict[str, Any]:
    original_nodes = workspace.get("nodes", [])
    original_edges = workspace.get("edges", [])
    anchor = workspace.get("anchor")
    anchor_id = anchor.get("id") if anchor else None

    allowed_ids_by_type = {
        node["id"]
        for node in original_nodes
        if should_keep_node_by_type(node, filters) and should_keep_node_by_time(node, filters)
    }
    if anchor_id:
        allowed_ids_by_type.add(anchor_id)

    edges = [
        edge
        for edge in original_edges
        if edge["source_id"] in allowed_ids_by_type
        and edge["target_id"] in allowed_ids_by_type
        and edge_matches_filters(edge, filters)
    ]

    allowed_node_ids = set(allowed_ids_by_type)
    if filters.depth and anchor_id:
        allowed_node_ids = expand_by_depth(anchor_id, edges, filters.depth)
        allowed_node_ids.add(anchor_id)
    elif filters.relation_types or filters.min_weight > 0 or filters.start or filters.end:
        allowed_node_ids = {edge["source_id"] for edge in edges} | {edge["target_id"] for edge in edges}
        if anchor_id:
            allowed_node_ids.add(anchor_id)

    edges = [
        edge
        for edge in edges
        if edge["source_id"] in allowed_node_ids and edge["target_id"] in allowed_node_ids
    ]
    should_trim_to_connected_nodes = bool(
        filters.depth or filters.relation_types or filters.min_weight > 0 or filters.start or filters.end
    )
    connected_node_ids = (
        {edge["source_id"] for edge in edges} | {edge["target_id"] for edge in edges}
        if should_trim_to_connected_nodes
        else set(allowed_node_ids)
    )
    if anchor_id:
        connected_node_ids.add(anchor_id)

    nodes = [
        node
        for node in original_nodes
        if node["id"] in connected_node_ids and (node["id"] == anchor_id or should_keep_node_by_type(node, filters))
    ]
    timeline_focus = [
        item
        for item in workspace.get("timeline_focus", [])
        if not item.get("event_id") or item["event_id"] in {node["id"] for node in nodes}
    ]

    return {
        **workspace,
        "nodes": nodes,
        "edges": edges,
        "timeline_focus": timeline_focus,
        "stats": build_stats(nodes, edges, timeline_focus),
        "filters": serialize_filters(filters, original_nodes, original_edges),
    }


def should_keep_node_by_type(node: dict[str, Any], filters: GraphWorkspaceFilters) -> bool:
    return not filters.node_types or node["node_type"] in filters.node_types


def should_keep_node_by_time(node: dict[str, Any], filters: GraphWorkspaceFilters) -> bool:
    if node["node_type"] != "event" or (filters.start is None and filters.end is None):
        return True
    node_time = parse_datetime_filter(first_iso_meta(node))
    if node_time is None:
        return True
    if filters.start and node_time < filters.start:
        return False
    if filters.end and node_time > filters.end:
        return False
    return True


def first_iso_meta(node: dict[str, Any]) -> str | None:
    candidates = [node.get("subtitle"), *node.get("meta", [])]
    for value in candidates:
        if isinstance(value, str) and len(value) >= 10 and value[:4].isdigit():
            return value[:10]
    return None


def edge_matches_filters(edge: dict[str, Any], filters: GraphWorkspaceFilters) -> bool:
    if filters.relation_types and edge["edge_type"] not in filters.relation_types:
        return False
    if float(edge.get("weight") or 0.0) < filters.min_weight:
        return False
    return True


def expand_by_depth(anchor_id: str, edges: list[dict[str, Any]], depth: int) -> set[str]:
    visible = {anchor_id}
    frontier = {anchor_id}
    for _ in range(depth):
        next_frontier: set[str] = set()
        for edge in edges:
            if edge["source_id"] in frontier:
                next_frontier.add(edge["target_id"])
            if edge["target_id"] in frontier:
                next_frontier.add(edge["source_id"])
        next_frontier -= visible
        visible |= next_frontier
        frontier = next_frontier
        if not frontier:
            break
    return visible


def build_stats(nodes: list[dict[str, Any]], edges: list[dict[str, Any]], timeline_focus: list[dict[str, Any]]) -> dict[str, int]:
    conflicts = build_workspace_conflicts(nodes, edges)
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "event_count": sum(1 for node in nodes if node["node_type"] == "event"),
        "entity_count": sum(1 for node in nodes if node["node_type"] == "entity"),
        "timeline_count": len(timeline_focus),
        "conflict_count": len(conflicts),
        "low_confidence_edge_count": sum(1 for edge in edges if float(edge.get("weight") or 0) < 0.55),
        "orphan_node_count": len(find_orphan_node_ids(nodes, edges)),
    }


def serialize_filters(
    filters: GraphWorkspaceFilters,
    original_nodes: list[dict[str, Any]],
    original_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "applied": {
            "node_types": sorted(filters.node_types),
            "relation_types": sorted(filters.relation_types),
            "start": filters.start.isoformat() if filters.start else None,
            "end": filters.end.isoformat() if filters.end else None,
            "min_weight": filters.min_weight,
            "depth": filters.depth,
        },
        "available": {
            "node_types": sorted({node["node_type"] for node in original_nodes}),
            "relation_types": sorted({edge["edge_type"] for edge in original_edges}),
        },
    }


def build_event_workspace(db: Session, *, user_id: str, event_id: str) -> dict[str, Any]:
    detail = event_query.get_event_detail(db, user_id=user_id, event_id=event_id)
    anchor = {
        "id": detail["id"],
        "node_type": "event",
        "label": detail["title"],
        "subtitle": detail.get("time_text") or detail.get("event_type") or "事件锚点",
        "href": f"/events/{detail['id']}",
    }

    nodes = [
        build_event_node(
            detail,
            is_anchor=True,
            actions=[
                action("打开事件", f"/events/{detail['id']}", "open", "secondary"),
                action("进入审核", f"/review/events/{detail['id']}", "review", "info"),
                action("进入校对", f"/curation/events/{detail['id']}", "curation", "primary"),
            ],
            context_lines=[
                f"参与角色 {len(detail.get('participants', []))} 个",
                f"关联事件 {len(detail.get('related_events', []))} 个",
                f"来源卷宗 {detail['source_note_title']}" if detail.get("source_note_title") else "当前未绑定来源卷宗",
            ],
        )
    ]
    edges: list[dict[str, Any]] = []

    for participant in detail.get("participants", []):
        nodes.append(
            build_entity_node(
                {
                    "id": participant["id"],
                    "display_name": participant["display_name"],
                    "entity_type": participant["entity_type"],
                    "description": participant.get("role") or participant.get("relation_type"),
                },
                actions=[
                    action("人物故事", f"/story/entity/{participant['id']}", "open_story", "secondary"),
                    action("人物审核", f"/review/entities/{participant['id']}", "review", "info"),
                    action("人物校对", f"/curation/entities/{participant['id']}", "curation", "primary"),
                ],
                context_lines=[
                    participant.get("role") or "未标注角色",
                    participant.get("relation_type") or "参与关系",
                ],
                importance=0.58,
            )
        )
        edges.append(
            {
                "source_id": detail["id"],
                "target_id": participant["id"],
                "edge_type": "participates_in",
                "label": participant.get("role") or participant.get("relation_type") or "参与",
                "weight": round(float(participant.get("confidence_score") or 0.72), 2),
            }
        )

    for related in detail.get("related_events", []):
        nodes.append(
            build_event_node(
                {
                    "id": related["id"],
                    "title": related["title"],
                    "summary": related.get("summary"),
                    "event_type": related.get("event_type"),
                    "time_text": related.get("time_text"),
                    "location_text": None,
                },
                actions=[
                    action("打开事件", f"/events/{related['id']}", "open", "secondary"),
                    action("进入审核", f"/review/events/{related['id']}", "review", "info"),
                ],
                context_lines=[
                    f"连接原因：{' / '.join(related.get('connection_reasons', [])[:3])}" if related.get("connection_reasons") else "等待更多连接原因",
                    f"共享人物：{'、'.join(related.get('shared_participants', [])[:3])}" if related.get("shared_participants") else "当前没有共享人物",
                    f"来源卷宗 {related['source_note_title']}" if related.get("source_note_title") else "未标注来源卷宗",
                ],
                importance=max(0.52, float(related.get("connection_score") or 0.52)),
            )
        )
        edges.append(
            {
                "source_id": detail["id"],
                "target_id": related["id"],
                "edge_type": "relates_to",
                "label": " / ".join(related.get("connection_reasons", [])[:3]) or "关联",
                "weight": round(float(related.get("connection_score") or 0.56), 2),
            }
        )

    timeline_focus = [
        {
            "id": detail["id"],
            "event_id": detail["id"],
            "title": detail["title"],
            "display_time": detail.get("time_text"),
            "href": f"/events/{detail['id']}",
            "kind": "anchor_event",
        }
    ]
    timeline_focus.extend(
        {
            "id": item["id"],
            "event_id": item["id"],
            "title": item["title"],
            "display_time": item.get("time_text"),
            "href": f"/events/{item['id']}",
            "kind": "related_event",
        }
        for item in detail.get("related_events", [])[:6]
    )

    return workspace_payload(
        scope="event",
        title=f"事件工作台：{detail['title']}",
        description="以当前事件为锚点，同时查看参与角色、相邻事件和可继续进入的治理动作。",
        anchor=anchor,
        nodes=dedupe_nodes(nodes),
        edges=edges,
        timeline_focus=timeline_focus,
    )


def build_entity_workspace(db: Session, *, user_id: str, entity_id: str) -> dict[str, Any]:
    detail = entity_query.get_entity_detail(db, user_id=user_id, entity_id=entity_id)
    anchor = {
        "id": detail["id"],
        "node_type": "entity",
        "label": detail["display_name"],
        "subtitle": detail.get("entity_type") or "人物锚点",
        "href": f"/story/entity/{detail['id']}",
    }

    nodes = [
        build_entity_node(
            detail,
            is_anchor=True,
            actions=[
                action("人物故事", f"/story/entity/{detail['id']}", "open_story", "secondary"),
                action("进入审核", f"/review/entities/{detail['id']}", "review", "info"),
                action("进入校对", f"/curation/entities/{detail['id']}", "curation", "primary"),
            ],
            context_lines=[
                f"别名 {len(detail.get('aliases', []))} 个",
                f"时间片段 {len(detail.get('timeline_fragments', []))} 个",
                f"关联事件 {len(detail.get('related_events', []))} 个",
            ],
        )
    ]
    edges: list[dict[str, Any]] = []

    fragment_event_ids: set[str] = set()
    for fragment in detail.get("timeline_fragments", []):
        fragment_event_ids.add(fragment["event_id"])
        nodes.append(
            build_event_node(
                {
                    "id": fragment["event_id"],
                    "title": fragment["title"],
                    "summary": fragment.get("summary"),
                    "event_type": fragment.get("event_type"),
                    "time_text": fragment.get("time_text"),
                    "location_text": fragment.get("location_text"),
                },
                actions=[
                    action("打开事件", f"/events/{fragment['event_id']}", "open", "secondary"),
                    action("事件审核", f"/review/events/{fragment['event_id']}", "review", "info"),
                ],
                context_lines=[
                    fragment.get("chapter_label") or "时间片段",
                    fragment.get("role") or fragment.get("relation_type") or "未标注角色",
                    f"来源卷宗 {fragment['source_note_title']}" if fragment.get("source_note_title") else "未标注来源卷宗",
                ],
                importance=0.66,
            )
        )
        edges.append(
            {
                "source_id": detail["id"],
                "target_id": fragment["event_id"],
                "edge_type": "appears_in",
                "label": fragment.get("role") or fragment.get("relation_type") or "时间片段",
                "weight": 0.78,
            }
        )

    for related in detail.get("related_events", []):
        if related["id"] in fragment_event_ids:
            continue
        nodes.append(
            build_event_node(
                {
                    "id": related["id"],
                    "title": related["title"],
                    "summary": related.get("summary"),
                    "event_type": related.get("event_type"),
                    "time_text": related.get("time_text"),
                    "location_text": related.get("location_text"),
                },
                actions=[
                    action("打开事件", f"/events/{related['id']}", "open", "secondary"),
                    action("事件审核", f"/review/events/{related['id']}", "review", "info"),
                ],
                context_lines=[
                    related.get("role") or related.get("relation_type") or "侧向事件",
                    related.get("location_text") or "未标注地点",
                ],
                importance=0.54,
            )
        )
        edges.append(
            {
                "source_id": detail["id"],
                "target_id": related["id"],
                "edge_type": "related_to_entity",
                "label": related.get("role") or related.get("relation_type") or "侧向事件",
                "weight": 0.6,
            }
        )

    timeline_focus = [
        {
            "id": item["event_id"],
            "event_id": item["event_id"],
            "title": item["title"],
            "display_time": item.get("time_text"),
            "href": f"/events/{item['event_id']}",
            "kind": "timeline_fragment",
        }
        for item in detail.get("timeline_fragments", [])[:8]
    ]

    return workspace_payload(
        scope="entity",
        title=f"人物工作台：{detail['display_name']}",
        description="以人物为锚点查看时间骨架、侧向事件和人物治理入口。",
        anchor=anchor,
        nodes=dedupe_nodes(nodes),
        edges=edges,
        timeline_focus=timeline_focus,
    )


def build_overview_workspace(db: Session, *, user_id: str) -> dict[str, Any]:
    overview = timeline_query.get_timeline_overview(db, user_id=user_id)
    nodes = []
    for item in overview.get("nodes", []):
        actions = [action("打开节点", item["href"], "open", "secondary")]
        if item["node_type"] == "event":
            actions.append(action("进入审核", f"/review/events/{item['id']}", "review", "info"))
            actions.append(action("进入校对", f"/curation/events/{item['id']}", "curation", "primary"))
        elif item["node_type"] == "entity":
            actions.append(action("人物审核", f"/review/entities/{item['id']}", "review", "info"))
            actions.append(action("人物校对", f"/curation/entities/{item['id']}", "curation", "primary"))
        nodes.append(
            {
                **item,
                "is_anchor": False,
                "inspector": {
                    "id": item["id"],
                    "node_type": item["node_type"],
                    "title": item["label"],
                    "summary": "这是从全局图谱里抽出的近期高频节点，可继续深入到事件、人物或治理页面。",
                    "chips": [meta for meta in item.get("meta", []) if meta][:4],
                    "context_lines": [
                        f"当前节点连接 {sum(1 for edge in overview.get('edges', []) if edge['source_id'] == item['id'] or edge['target_id'] == item['id'])} 条关系线"
                    ],
                    "actions": actions,
                },
            }
        )

    anchor = None
    if nodes:
        first = nodes[0]
        anchor = {
            "id": first["id"],
            "node_type": first["node_type"],
            "label": first["label"],
            "subtitle": first["subtitle"],
            "href": first["href"],
        }

    timeline_focus = [
        {
            "id": item["id"],
            "event_id": item.get("event_id"),
            "title": item["title"],
            "display_time": item.get("display_time"),
            "href": f"/events/{item['event_id']}" if item.get("event_id") else "/timeline",
            "kind": "timeline_focus",
        }
        for item in overview.get("timeline_focus", [])[:10]
    ]

    return workspace_payload(
        scope="overview",
        title="图谱总览工作台",
        description="从近期事件和高频人物开始，先看网络重心，再进入具体节点的治理流。",
        anchor=anchor,
        nodes=nodes,
        edges=overview.get("edges", []),
        timeline_focus=timeline_focus,
    )


def build_event_node(
    item: dict[str, Any],
    *,
    is_anchor: bool = False,
    actions: list[dict[str, Any]] | None = None,
    context_lines: list[str] | None = None,
    importance: float | None = None,
) -> dict[str, Any]:
    return {
        "id": item["id"],
        "node_type": "event",
        "label": item["title"],
        "subtitle": item.get("time_text") or item.get("event_type") or "事件节点",
        "href": f"/events/{item['id']}",
        "importance": importance if importance is not None else 0.76,
        "meta": [value for value in [item.get("event_type"), item.get("time_text"), item.get("location_text")] if value],
        "is_anchor": is_anchor,
        "inspector": {
            "id": item["id"],
            "node_type": "event",
            "title": item["title"],
            "summary": item.get("summary"),
            "chips": [value for value in [item.get("event_type"), item.get("time_text"), item.get("location_text")] if value],
            "context_lines": [line for line in (context_lines or []) if line],
            "actions": actions or [],
        },
    }


def build_entity_node(
    item: dict[str, Any],
    *,
    is_anchor: bool = False,
    actions: list[dict[str, Any]] | None = None,
    context_lines: list[str] | None = None,
    importance: float | None = None,
) -> dict[str, Any]:
    aliases = item.get("aliases") or []
    chips = [value for value in [item.get("entity_type"), *aliases[:2]] if value]
    return {
        "id": item["id"],
        "node_type": "entity",
        "label": item["display_name"],
        "subtitle": item.get("entity_type") or "角色节点",
        "href": f"/story/entity/{item['id']}",
        "importance": importance if importance is not None else 0.64,
        "meta": chips,
        "is_anchor": is_anchor,
        "inspector": {
            "id": item["id"],
            "node_type": "entity",
            "title": item["display_name"],
            "summary": item.get("description"),
            "chips": chips,
            "context_lines": [line for line in (context_lines or []) if line],
            "actions": actions or [],
        },
    }


def dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for node in nodes:
        key = (node["node_type"], node["id"])
        current = deduped.get(key)
        if current is None or (node.get("is_anchor") and not current.get("is_anchor")):
            deduped[key] = node
    return list(deduped.values())


def workspace_payload(
    *,
    scope: str,
    title: str,
    description: str,
    anchor: dict[str, Any] | None,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    timeline_focus: list[dict[str, Any]],
) -> dict[str, Any]:
    conflicts = build_workspace_conflicts(nodes, edges)
    return {
        "scope": scope,
        "title": title,
        "description": description,
        "anchor": anchor,
        "nodes": nodes,
        "edges": edges,
        "timeline_focus": timeline_focus,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "event_count": sum(1 for node in nodes if node["node_type"] == "event"),
            "entity_count": sum(1 for node in nodes if node["node_type"] == "entity"),
            "timeline_count": len(timeline_focus),
            "conflict_count": len(conflicts),
            "low_confidence_edge_count": sum(1 for edge in edges if float(edge.get("weight") or 0) < 0.55),
            "orphan_node_count": len(find_orphan_node_ids(nodes, edges)),
        },
        "conflicts": conflicts,
    }


def finalize_workspace(db: Session, workspace: dict[str, Any], *, user_id: str) -> dict[str, Any]:
    conflicts = build_workspace_conflicts(workspace.get("nodes", []), workspace.get("edges", []))
    return {
        **workspace,
        "conflicts": conflicts,
        "stats": {
            **workspace.get("stats", {}),
            "conflict_count": len(conflicts),
            "low_confidence_edge_count": sum(1 for edge in workspace.get("edges", []) if float(edge.get("weight") or 0) < 0.55),
            "orphan_node_count": len(find_orphan_node_ids(workspace.get("nodes", []), workspace.get("edges", []))),
        },
        "recent_actions": list_graph_actions(db, user_id=user_id),
    }


def build_workspace_conflicts(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    node_ids = {node["id"] for node in nodes}
    node_by_id = {node["id"]: node for node in nodes}
    edge_pairs: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for edge in edges:
        source_id = edge["source_id"]
        target_id = edge["target_id"]
        weight = float(edge.get("weight") or 0)
        if weight < 0.55:
            conflicts.append(
                {
                    "id": f"low-confidence-{source_id}-{target_id}-{edge['edge_type']}",
                    "severity": "medium",
                    "conflict_type": "low_confidence_edge",
                    "title": "低置信关系",
                    "summary": f"{node_by_id.get(source_id, {}).get('label', source_id)} 与 {node_by_id.get(target_id, {}).get('label', target_id)} 的 `{edge['label']}` 权重偏低。",
                    "node_ids": [source_id, target_id],
                    "edge_label": edge.get("label"),
                    "href": graph_href_for_node(source_id, node_by_id),
                }
            )
        pair_key = (source_id, target_id, edge["edge_type"])
        edge_pairs.setdefault(pair_key, []).append(edge)

    for (source_id, target_id, edge_type), pair_edges in edge_pairs.items():
        labels = {edge.get("label") for edge in pair_edges if edge.get("label")}
        if len(labels) > 1:
            conflicts.append(
                {
                    "id": f"relation-label-conflict-{source_id}-{target_id}-{edge_type}",
                    "severity": "high",
                    "conflict_type": "relation_label_conflict",
                    "title": "关系标签冲突",
                    "summary": f"同一对节点存在多个 `{edge_type}` 标签：{' / '.join(sorted(labels))}",
                    "node_ids": [source_id, target_id],
                    "edge_label": edge_type,
                    "href": graph_href_for_node(source_id, node_by_id),
                }
            )

    for node_id in find_orphan_node_ids(nodes, edges):
        node = node_by_id[node_id]
        conflicts.append(
            {
                "id": f"orphan-node-{node_id}",
                "severity": "low",
                "conflict_type": "orphan_node",
                "title": "孤立节点",
                "summary": f"{node['label']} 当前没有可见关系，可能需要扩大过滤范围或补充连接。",
                "node_ids": [node_id],
                "edge_label": None,
                "href": graph_href_for_node(node_id, node_by_id),
            }
        )
    return conflicts[:12]


def find_orphan_node_ids(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> set[str]:
    connected_ids = {edge["source_id"] for edge in edges} | {edge["target_id"] for edge in edges}
    return {node["id"] for node in nodes if not node.get("is_anchor") and node["id"] not in connected_ids}


def graph_href_for_node(node_id: str, node_by_id: dict[str, dict[str, Any]]) -> str:
    node = node_by_id.get(node_id)
    if not node:
        return "/graph"
    if node["node_type"] == "event":
        return f"/graph?event_id={node_id}"
    if node["node_type"] == "entity":
        return f"/graph?entity_id={node_id}"
    return "/graph"


def list_graph_actions(db: Session, *, user_id: str, limit: int = 8) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(ReviewAction)
        .where(
            ReviewAction.user_id == user_id,
            ReviewAction.action_type.in_(
                [
                    "update_entity",
                    "update_event",
                    "upsert_event_participant",
                    "remove_event_participant",
                    "add_relation",
                    "upsert_relation",
                    "update_relation",
                    "remove_relation",
                ]
            ),
        )
        .order_by(ReviewAction.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": row.id,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "action_type": row.action_type,
            "status_before": row.status_before,
            "status_after": row.status_after,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "summary": f"{row.target_type} {row.target_id} 执行了 {row.action_type}",
        }
        for row in rows
    ]


def build_timeline_context_for_node(
    *,
    node: dict[str, Any],
    workspace: dict[str, Any],
    connected_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    timeline_focus = workspace.get("timeline_focus", [])
    if node["node_type"] == "event":
        matched = [item for item in timeline_focus if item.get("event_id") == node["id"]]
        if matched:
            return matched
        return timeline_focus[:4]

    connected_event_ids = {
        item["id"] for item in connected_nodes if item["node_type"] == "event"
    }
    matched = [
        item for item in timeline_focus if item.get("event_id") in connected_event_ids
    ]
    return matched[:6] if matched else timeline_focus[:6]


def action(label: str, href: str, action_type: str, variant: str) -> dict[str, Any]:
    return {
        "label": label,
        "href": href,
        "action_type": action_type,
        "variant": variant,
    }
