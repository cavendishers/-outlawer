# Phase 12 Event Curation Plan

Status: `DONE`

Verified on `2026-04-18` with:

- `python3 -m compileall server/app server/tests server/scripts`
- `npm run build` in `web/`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_curation_flow.py`

## Goal

Deliver the first manual graph curation slice focused on events so the knowledge graph can be corrected without re-running the extraction pipeline.

## Scope

This phase includes:

- event field editing
- event participant add/remove
- event-centered relation add/remove
- event curation web page
- end-to-end verification

This phase does not include:

- full entity editor
- generic graph canvas editing
- relation in-place editing
- collaborative moderation

## Delivered APIs

- `GET /api/v1/curation/events/{event_id}`
- `PATCH /api/v1/curation/events/{event_id}`
- `POST /api/v1/curation/events/{event_id}/participants`
- `DELETE /api/v1/curation/events/{event_id}/participants/{entity_id}`
- `POST /api/v1/curation/events/{event_id}/relations`
- `DELETE /api/v1/curation/events/{event_id}/relations/{relation_id}`

## Delivered UI

- `/curation/events/[id]`

The page supports:

- editing title, summary, description, type, status, time, and location
- adding or removing participants
- adding or removing extra graph relations
- returning to the standard event detail view

## Consistency Rules

- manual edits do not overwrite raw assets or extraction runs
- participant edits update both `event_entities` and the mirrored participant relation rows
- event field edits keep `timeline_items` aligned for title, summary, display time, sort time, and time precision
- relation management uses the existing `relations` table and is scoped to the current user

## Follow-Up

Recommended next step after this phase:

- build the first entity editor and extend curation from event-centered maintenance to broader graph maintenance
