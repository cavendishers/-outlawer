# AI Extraction Format

## Goal

Define the structured JSON contract returned by the AI extraction pipeline before normalized database writes.

This format is intended for:

- LLM output validation
- Celery worker post-processing
- replay and debugging
- versioned extraction evolution

## Top-Level Shape

```json
{
  "source": {},
  "summary": {},
  "entities": [],
  "events": [],
  "relations": [],
  "timeline": [],
  "similarity_hints": [],
  "style_payload": {}
}
```

## Source Block

Tracks what input was analyzed.

```json
{
  "source": {
    "note_id": "note_xxx",
    "asset_id": "asset_xxx",
    "content_type": "text",
    "language": "zh-CN",
    "extractor_name": "knowledge_pipeline",
    "extractor_version": "v1"
  }
}
```

## Summary Block

Stores the canonical note-level interpretation.

```json
{
  "summary": {
    "title": "Project kickoff discussion",
    "short_summary": "Zhang San joined the kickoff meeting and discussed the first task split.",
    "canonical_text": "Normalized and cleaned text for downstream extraction.",
    "category": "project",
    "tags": ["kickoff", "project", "zhangsan"]
  }
}
```

## Entities Block

Each entity should include evidence and a resolution hint.

```json
{
  "entities": [
    {
      "temp_id": "ent_1",
      "entity_type": "person",
      "name": "张三",
      "canonical_name": "张三",
      "aliases": ["三哥"],
      "description": "Project member",
      "confidence": 0.95,
      "evidence": [
        {
          "text": "张三在会上提出了初版计划",
          "start": 12,
          "end": 24
        }
      ],
      "resolution_hint": {
        "normalized_name": "张三",
        "possible_existing_entity_ids": ["entity_abc"],
        "match_strategy": "name+context"
      }
    }
  ]
}
```

## Events Block

Each event should be self-contained enough to survive intermediate processing.

```json
{
  "events": [
    {
      "temp_id": "evt_1",
      "title": "项目启动会议",
      "event_type": "meeting",
      "summary": "项目组召开启动会议，讨论初版分工。",
      "description": "张三、李四参加项目启动会议，并提出初版方案。",
      "time": {
        "time_text": "昨天下午",
        "start_time": "2026-04-16T14:00:00+08:00",
        "end_time": null,
        "time_precision": "day",
        "timeline_sort_time": "2026-04-16T14:00:00+08:00"
      },
      "participants": [
        {
          "entity_temp_id": "ent_1",
          "role": "participant",
          "relation_type": "participates_in"
        }
      ],
      "locations": [
        {
          "name": "会议室A",
          "entity_temp_id": null
        }
      ],
      "confidence": 0.88,
      "evidence": [
        {
          "text": "昨天下午张三和李四开了项目启动会",
          "start": 0,
          "end": 18
        }
      ],
      "resolution_hint": {
        "possible_existing_event_ids": ["event_xyz"],
        "match_strategy": "time+participants+semantic"
      }
    }
  ]
}
```

## Relations Block

Relations should be explicit rather than inferred only in application code.

```json
{
  "relations": [
    {
      "source_ref": {
        "type": "entity",
        "temp_id": "ent_1"
      },
      "relation_type": "participates_in",
      "target_ref": {
        "type": "event",
        "temp_id": "evt_1"
      },
      "confidence": 0.96,
      "evidence": [
        {
          "text": "张三参加了启动会",
          "start": 20,
          "end": 29
        }
      ]
    },
    {
      "source_ref": {
        "type": "note",
        "id": "note_xxx"
      },
      "relation_type": "source_of",
      "target_ref": {
        "type": "event",
        "temp_id": "evt_1"
      },
      "confidence": 1.0,
      "evidence": []
    }
  ]
}
```

## Timeline Block

This is a projection-friendly structure for timeline items.

```json
{
  "timeline": [
    {
      "event_temp_id": "evt_1",
      "title": "项目启动会议",
      "summary": "讨论项目初版分工",
      "display_time": "昨天下午",
      "sort_time": "2026-04-16T14:00:00+08:00",
      "time_precision": "day",
      "importance_score": 0.72
    }
  ]
}
```

## Similarity Hints Block

Similarity hints are candidates, not final truth.

```json
{
  "similarity_hints": [
    {
      "target_type": "note",
      "target_id": "note_old_1",
      "reason": "同样提到了张三和项目启动会",
      "confidence": 0.78
    },
    {
      "target_type": "event",
      "target_id": "event_old_2",
      "reason": "时间和参与人物高度接近",
      "confidence": 0.81
    }
  ]
}
```

## Style Payload Block

Stylized presentation should be generated as structured content first.

```json
{
  "style_payload": {
    "theme": "chunibyo",
    "title": "命运序章：启动之刻",
    "character_cards": [
      {
        "entity_temp_id": "ent_1",
        "display_name": "张三",
        "epithet": "初始策划者",
        "aura": "在沉默中布下最初的棋局"
      }
    ],
    "event_narrative": [
      {
        "event_temp_id": "evt_1",
        "headline": "序列零号会议",
        "body": "那是命运齿轮开始咬合的瞬间。"
      }
    ]
  }
}
```

## Processing Rules

- save the raw extraction JSON before normalization
- store each extraction pass in `extraction_runs` so reprocessing keeps history
- project normalized entities, events, relations, timeline items, embeddings, and style views from the saved extraction
- convert `temp_id` references into real database ids during post-processing
- attach evidence rows for entities, events, and relations
- use `resolution_hint` only as a candidate source, not final authority
- use similarity hints as inputs to merge candidate generation

## Validation Rules

- every entity must include `temp_id`, `entity_type`, `canonical_name`, and `confidence`
- every event must include `temp_id`, `title`, and a `time` block
- every relation must include source, target, and `relation_type`
- evidence items should preserve source text spans whenever available
- extractor metadata should be recorded in `source`
