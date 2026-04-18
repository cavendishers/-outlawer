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
- `POST /api/v1/notes/{note_id}/reprocess`

Responsibilities:

- create knowledge entries from assets
- read note summaries and canonical text
- trigger async reprocessing
- preserve extraction history through `extraction_runs`
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
