from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import entity_query_service, event_query_service, timeline_query_service


def get_graph_workspace(
    db: Session,
    *,
    user_id: str,
    event_id: str | None = None,
    entity_id: str | None = None,
) -> dict[str, Any]:
    if event_id:
        return build_event_workspace(db, user_id=user_id, event_id=event_id)
    if entity_id:
        return build_entity_workspace(db, user_id=user_id, entity_id=entity_id)
    return build_overview_workspace(db, user_id=user_id)


def build_event_workspace(db: Session, *, user_id: str, event_id: str) -> dict[str, Any]:
    detail = event_query_service.get_event_detail(db, user_id=user_id, event_id=event_id)
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
    detail = entity_query_service.get_entity_detail(db, user_id=user_id, entity_id=entity_id)
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
    overview = timeline_query_service.get_timeline_overview(db, user_id=user_id)
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
        },
    }


def action(label: str, href: str, action_type: str, variant: str) -> dict[str, Any]:
    return {
        "label": label,
        "href": href,
        "action_type": action_type,
        "variant": variant,
    }
