# Phase 11 Review Workflow Plan

Status: `DONE`

Verified on `2026-04-18` with:

- `python3 -m compileall server/app server/tests server/scripts`
- `npm run build` in `web/`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api alembic upgrade head`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_review_flow.py`

## Goal

Build the first operational review workflow for extracted entities and events so the knowledge graph can be corrected, merged, and trusted over time.

This phase is the next recommended delivery phase after the current MVP and architecture hardening work.

## Why This Phase First

- extraction quality now depends on human review more than raw pipeline expansion
- duplicate people and duplicate events will accumulate without governance tools
- the current graph is displayable, but not yet maintainable
- this phase directly improves search, timeline, people pages, and event pages at the same time

## Scope

This phase focuses on:

- merge candidate review
- entity merge actions
- event merge actions
- alias confirmation for entities
- audit logging for review actions
- a first review UI and e2e flow

## Out Of Scope

These should stay out of Phase 11 unless required by implementation:

- full graph editing
- manual relation editor
- multi-user collaboration
- extraction diff/replay UI
- generic admin console

## Delivery Definition

Phase 11 is complete when:

- merge candidates can be listed and filtered
- a candidate can be accepted or rejected
- accepting a candidate can merge two entities or two events safely
- alias confirmation updates canonical alias records
- review actions are auditable
- web UI supports the main review loop
- e2e covers the happy path and one rejection path

## Backend API Tasks

### Review Queue

- `GET /api/v1/review/merge-candidates`
  - supports `object_type`, `status`, `page`, `page_size`
  - returns source object summary, candidate summary, score, reason, and reviewability flags

- `GET /api/v1/review/merge-candidates/{candidate_id}`
  - returns full review context
  - includes source object snapshot, candidate object snapshot, linked notes/events count, and evidence summary

### Review Actions

- `POST /api/v1/review/merge-candidates/{candidate_id}/reject`
  - payload: `reason`, optional `note`
  - updates candidate status to `rejected`
  - writes review action log

- `POST /api/v1/review/merge-candidates/{candidate_id}/accept`
  - payload includes action details
  - entity candidate:
    - `resolution`: `merge` or `alias_only`
    - `survivor_id`
  - event candidate:
    - `resolution`: `merge`
    - `survivor_id`
  - writes review action log
  - marks candidate as `accepted`

### Entity Review Context

- `GET /api/v1/review/entities/{entity_id}/context`
  - linked notes count
  - linked events count
  - aliases
  - recent timeline fragments
  - candidate list for this entity

### Event Review Context

- `GET /api/v1/review/events/{event_id}/context`
  - participant list
  - source note
  - related timeline items
  - candidate list for this event

## Database Tasks

### New Tables

Add `review_actions`:

```text
id
user_id
target_type
target_id
action_type
status_before
status_after
payload_json
created_at
updated_at
```

Purpose:

- audit trail for reject, accept, merge, and alias confirmation actions

Add `entity_merge_history`:

```text
id
user_id
survivor_entity_id
merged_entity_id
merge_reason
payload_json
created_at
updated_at
```

Add `event_merge_history`:

```text
id
user_id
survivor_event_id
merged_event_id
merge_reason
payload_json
created_at
updated_at
```

### Existing Table Changes

Update `merge_candidates`:

- ensure statuses explicitly support:
  - `pending`
  - `accepted`
  - `rejected`
  - `superseded`
- optionally add:
  - `reviewed_at`
  - `review_note`

### Merge Logic Requirements

Entity merge must re-point:

- `note_entities.entity_id`
- `event_entities.entity_id`
- `style_views.target_id` where `target_type=entity`
- `embeddings.owner_id` where `owner_type=entity`
- `merge_candidates.source_id/candidate_id` where relevant

Event merge must re-point:

- `note_events.event_id`
- `event_entities.event_id`
- `timeline_items.event_id`
- `style_views.target_id` where `target_type=event`
- `embeddings.owner_id` where `owner_type=event`
- `merge_candidates.source_id/candidate_id` where relevant

Alias confirmation must:

- write to `entity_aliases`
- optionally refresh `entities.alias_json` as display cache if that field remains during transition

## Backend Service Tasks

### New Services

- `review_service.py`
  - queue listing
  - review action orchestration
  - reject flow
  - accept flow

- `merge_service.py`
  - entity merge
  - event merge
  - survivor record selection rules
  - dependent reference rewrites

- `review_query_service.py`
  - build entity review context
  - build event review context
  - build candidate detail payload

### Rules To Implement

- merge must be transactional
- raw assets and extraction runs are never deleted in this phase
- rejected candidates remain queryable for audit
- accepted candidates should not reappear as pending
- if two objects cannot be safely merged, return a reviewable error instead of partial writes

## Frontend Tasks

### New Pages

- `/review`
  - queue list
  - tabs or filters for `entity` and `event`
  - candidate cards with score, reason, source label, candidate label

- `/review/entities/[id]`
  - entity review context page
  - aliases
  - linked events
  - timeline fragments
  - candidate comparison area

- `/review/events/[id]`
  - event review context page
  - participant comparison
  - time/location/source note comparison
  - candidate comparison area

### Core UI Actions

- reject candidate
- accept as merge
- accept as alias-only for entity candidates
- choose survivor object when merging
- show action result and refresh queue state

### UX Constraints

- keep review actions explicit and irreversible-looking
- show side-by-side object comparison before merge
- clearly separate `reject`, `alias only`, and `merge`
- show post-action feedback immediately

## E2E Verification Tasks

### API E2E

Add to `server/scripts/e2e_api_flow.py` or a new phase-specific script:

1. create two similar notes
2. wait for extraction completion
3. fetch merge candidate queue
4. reject one candidate and verify status change
5. accept one entity candidate and verify merge result
6. verify entity links now point to survivor entity
7. verify review action log exists

### Web E2E

Recommended first-pass manual or scripted flow:

1. log in
2. open `/review`
3. filter entity candidates
4. open candidate detail
5. reject one candidate
6. accept one candidate as merge
7. verify people page reflects merged result

### Regression Checks

- run `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest`
- run `python3 server/scripts/e2e_api_flow.py --phase full`
- run the new review-flow e2e
- run `npm run build` in `web/`

## Suggested Build Order

1. add migration files for review tables and candidate status expansion
2. implement backend merge and review services
3. expose review APIs
4. add backend tests for accept/reject/merge
5. build `/review` queue page
6. build entity and event review context pages
7. add e2e coverage

## Risks

- merge logic can corrupt graph references if not fully transactional
- alias handling can become inconsistent while `alias_json` and `entity_aliases` coexist
- accepted merges may affect story views and search if dependent projections are not refreshed

## Recommended Completion Evidence

Phase 11 should only be marked complete after:

- migration applies cleanly in Docker
- entity merge test passes
- event merge test passes
- reject flow test passes
- review UI flow is manually verified
- review-flow e2e passes
