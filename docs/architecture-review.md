# Architecture Review And Iteration Plan

## Executive Summary

Current stack selection is reasonable for this product:

- `Next.js + TypeScript + Tailwind CSS` fits a graph-heavy interactive product
- `FastAPI + PostgreSQL + pgvector + Redis + RabbitMQ + MinIO` is a strong Docker-first backend baseline
- separating raw assets, extracted knowledge, and stylized story views is the right product-level modeling decision

The current issues are mostly internal-boundary issues rather than stack issues:

- route files still mix request handling, query logic, and response assembly
- list endpoints were inconsistent
- job dispatch was hardcoded to a single task type
- a few model choices are still MVP shortcuts and will slow future graph work

This iteration keeps the current stack and improves the internal structure so future capabilities can be added with lower cost.

## What Is Already Good

- raw source preservation is correct and should remain unchanged
- async ingestion and extraction are correctly separated from user-facing writes
- event-centric graph modeling is the right backbone for people, timeline, and relation views
- Docker-first deployment and Alembic-based migrations are the right operational defaults
- canonical knowledge and stylized presentation are already separated conceptually

## Structural Weaknesses

### API Layer

- routes are still dict-heavy and not consistently schema-driven
- list endpoints were not uniformly paginated
- serialization logic was duplicated across multiple route files
- search aggregation used to live directly in the route module

### Application Layer

- `pipeline_service.py` is still too monolithic
- job dispatch was tied to a single pipeline path
- read/query concerns are only partially separated from write/orchestration concerns

### Data Model

- `entities.first_seen_at` and `entities.last_seen_at` were stored as strings
- `alias_json` still exists, but it is now transitional cache data while `entity_aliases` is canonical
- vectors are now centralized in `embeddings`
- participant facts are safest when they stay canonical in `event_entities` rather than being mirrored into generic `relations`

### Frontend Contract

- several frontend contracts are still implicit rather than strongly typed
- search, timeline, people, and event pages would benefit from a more explicit read-model contract

## Target Architecture

Recommended backend layering:

```text
api routes
  -> application services
  -> query services
  -> domain/data models
  -> serializers/presenters
```

Recommended responsibilities:

- route layer: auth, request parsing, status code handling
- application service layer: ingestion, extraction orchestration, retries, write workflows
- query service layer: search, list views, graph traversals, timeline views
- serializer/presenter layer: stable response payload assembly

## API Direction

Keep APIs in three families:

- write APIs: upload, create note, reprocess, retry, merge-review actions
- read APIs: notes, entities, events, timeline, story views, graph views
- async APIs: jobs and future batch processing flows

API rules:

- keep the response envelope stable
- require pagination metadata on list endpoints
- keep upload and processing separate
- return UI-facing read models instead of raw ORM-shaped payloads
- introduce dedicated review/action endpoints when graph curation is added

## Database Direction

Recommended database stance:

- keep canonical graph tables normalized
- keep raw and derived media outputs append-only where practical
- use projection tables for high-frequency UI reads
- centralize embeddings progressively instead of duplicating vectors across tables

Recommended long-term shape:

- `raw_assets` + `asset_derivatives` remain source and preprocessing layers
- `notes`, `entities`, `events`, `relations`, `timeline_items` remain the canonical graph layer
- `style_views` remains derived presentation
- `entity_aliases` becomes the canonical alias store over time
- `embeddings` becomes the single long-term vector store

## Changes Applied In This Iteration

- shared response helpers in `server/app/core/responses.py`
- shared pagination helpers in `server/app/core/pagination.py`
- shared API serializers in `server/app/api/serializers.py`
- search aggregation moved into `server/app/services/search_service.py`
- generic job dispatch abstraction in `server/app/services/job_dispatcher.py`
- key list endpoints standardized on pagination metadata
- entity first/last seen fields converted to real timestamp columns with Alembic migration
- pipeline orchestration split so raw asset text derivation and graph projection writes are no longer embedded in one large service file
- alias reads and writes now flow through `entity_aliases`
- note chunk vectors were removed and vector truth now lives in `embeddings`
- participant duplication into `relations(participates_in)` was removed so event participation stays canonical in `event_entities`

## Recommended Next Refactors

### Now

- add explicit Pydantic request and response schemas for public endpoints
- add query services for entities, events, and timeline read models

### Next

- enrich extraction and projection version metadata
- treat `alias_json` as cache/display data only until it can be removed entirely
- extend centralized embeddings with richer metadata when retrieval needs it
- keep tightening replay-safe projection boundaries

### Later

- add graph curation workflows
- add workspace-level isolation if multi-user collaboration is introduced
- add extractor/model version replay tools for reprocessing and auditability

## Domain Rules To Keep Stable

- `Entity` is identity
- `Event` is the timeline anchor
- `Relation` is generalized graph linkage
- `TimelineItem` is a projection, not the source of truth
- `StyleView` is display-only derivative content

## Final Recommendation

Do not replace the current stack.

The right move is to keep tightening internal boundaries:

- stronger contracts
- cleaner read/write separation
- less logic in routes
- fewer duplicated representations
- clearer projection models for the UI

That will make the next wave of multimodal, graph, and search capabilities much easier to build.
