# API Contract

## Versioning

All public endpoints should be exposed under:

- `/api/v1`

## Response Envelope

Standard response body:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

## Common Conventions

- Authenticated APIs use bearer tokens in the `Authorization` header.
- List endpoints should support pagination.
- Long-running AI tasks return a tracked `job_id`.
- Upload and processing are separate operations.
- Job status values are `pending`, `running`, `completed`, and `failed`.

## Pagination Parameters

- `page`
- `page_size`
- `sort_by`
- `sort_order`

Paginated list response shape:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20,
    "total_pages": 0
  }
}
```

Current rule:

- list-style read endpoints should return pagination metadata
- clients should continue reading `data.items` as the primary collection field

## Endpoint Modules

### Auth

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Assets

- `POST /api/v1/assets/upload`
- `GET /api/v1/assets`
- `GET /api/v1/assets/{asset_id}`
- `GET /api/v1/assets/{asset_id}/raw`

Responsibilities:

- upload text, audio, image, and video
- fetch asset metadata
- fetch raw material references
- proxy file uploads into MinIO from the API layer
- return original text or a presigned `raw_url` for raw reads

### Notes

- `POST /api/v1/notes`
- `GET /api/v1/notes`
- `GET /api/v1/notes/{note_id}`
- `GET /api/v1/notes/{note_id}/extraction-runs`
- `GET /api/v1/notes/{note_id}/extraction-runs/{run_id}`
- `GET /api/v1/notes/{note_id}/extraction-runs/compare?base_run_id=...&candidate_run_id=...`
- `GET /api/v1/notes/{note_id}/replay-actions`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/approve`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/reject`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/apply`
- `POST /api/v1/notes/{note_id}/reprocess`

Responsibilities:

- create knowledge entries from assets
- read note summaries and canonical text
- trigger async reprocessing
- preserve extraction history through `extraction_runs`
- expose extraction run history, run summaries, and side-by-side diff snapshots
- create `ready_for_review` draft runs during reprocess when an active projection already exists
- approve or reject reviewable draft runs explicitly before changing the current projection
- apply a selected historical extraction run back into the current note projection
- expose replay audit history for automatic and manual projection-apply actions
- return paginated note collections for library-style UIs

### Entities

- `GET /api/v1/entities`
- `GET /api/v1/entities/{entity_id}`
- `GET /api/v1/entities/{entity_id}/events`

Responsibilities:

- people index
- organizations, places, concepts
- entity-related event browsing
- return entity read models optimized for people and graph views

### Events

- `GET /api/v1/events`
- `GET /api/v1/events/{event_id}`

Responsibilities:

- event browsing
- event detail
- return paginated event collections for index and timeline-adjacent UIs

### Timeline

- `GET /api/v1/timeline`
- `GET /api/v1/timeline/overview`
- `GET /api/v1/timeline/range`

Responsibilities:

- global timeline view
- date-range filtering
- return projection-friendly paginated timeline items

### Search

- `GET /api/v1/search`
- `GET /api/v1/search/unified`
- `GET /api/v1/search/similar/{note_id}`
- `GET /api/v1/search/merge-candidates`

Responsibilities:

- keyword search
- unified retrieval for notes, entities, events, and similar notes
- similarity recall using embeddings
- persisted merge candidate review

### Review

- `GET /api/v1/review/merge-candidates`
- `GET /api/v1/review/merge-candidates/{candidate_id}`
- `POST /api/v1/review/merge-candidates/{candidate_id}/reject`
- `POST /api/v1/review/merge-candidates/{candidate_id}/accept`
- `GET /api/v1/review/entities/{entity_id}/context`
- `POST /api/v1/review/entities/{entity_id}/aliases`
- `GET /api/v1/review/events/{event_id}/context`

Responsibilities:

- list and filter persisted merge candidates for entities and events
- accept or reject candidate review decisions
- merge duplicate entities or duplicate events into a chosen survivor
- confirm manual entity aliases without overwriting canonical knowledge records
- expose review-oriented entity and event context for web moderation flows
- preserve auditable review actions through `review_actions`

### Curation

- `GET /api/v1/curation/entities/{entity_id}`
- `PATCH /api/v1/curation/entities/{entity_id}`
- `POST /api/v1/curation/entities/{entity_id}/aliases`
- `DELETE /api/v1/curation/entities/{entity_id}/aliases/{alias_id}`
- `POST /api/v1/curation/entities/{entity_id}/relations`
- `PATCH /api/v1/curation/entities/{entity_id}/relations/{relation_id}`
- `DELETE /api/v1/curation/entities/{entity_id}/relations/{relation_id}`
- `GET /api/v1/curation/events/{event_id}`
- `PATCH /api/v1/curation/events/{event_id}`
- `POST /api/v1/curation/events/{event_id}/participants`
- `DELETE /api/v1/curation/events/{event_id}/participants/{entity_id}`
- `POST /api/v1/curation/events/{event_id}/relations`
- `PATCH /api/v1/curation/events/{event_id}/relations/{relation_id}`
- `DELETE /api/v1/curation/events/{event_id}/relations/{relation_id}`

Responsibilities:

- return an entity-oriented curation context with aliases, related events, and timeline fragments
- update canonical entity fields without touching raw source material
- manage trusted entity aliases through `entity_aliases`
- manage entity-centered graph links through `relations`
- return an event-oriented graph curation context for manual editing
- update canonical event fields without touching raw source material
- manage event participants through `event_entities`
- manage extra graph links through `relations`, including edit-in-place updates
- keep timeline projection fields in sync when an event is manually corrected

### Jobs

- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `POST /api/v1/jobs/{job_id}/retry`

Responsibilities:

- async pipeline status
- retry failed jobs
- expose paginated job history for inbox and retry UIs

### Story Views

- `GET /api/v1/views/story/note/{note_id}`
- `GET /api/v1/views/story/entity/{entity_id}`

Responsibilities:

- stylized chunibyo-style presentation views

## Recommended Async Flow

### Step 1: upload asset

- client uploads source content
- API stores metadata and proxies the raw object into MinIO
- API returns `asset_id`

### Step 2: create note

- client creates a note from `asset_id`
- API creates `note` and `job`
- API returns `note_id` and `job_id`

### Step 3: poll status

- client queries `GET /api/v1/jobs/{job_id}`
- once done, client fetches note, entities, timeline, and story views

### Step 4: review reprocess draft when needed

- if reprocess returns a run that `requires_review`, the active projection remains unchanged
- client can compare the current applied run with the candidate draft
- client approves with `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/approve`
- client rejects with `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/reject`
- historical rollback still uses `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/apply`
