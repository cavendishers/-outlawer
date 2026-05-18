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
- Core write endpoints should publish explicit Pydantic request schemas in OpenAPI and reject undeclared body fields.
- Core read endpoints should publish explicit response models in OpenAPI instead of anonymous `dict` payloads.

## Typed Write Request Contracts

The following write surfaces are now schema-driven rather than generic dictionary payloads:

- `POST /api/v1/notes` uses `NoteCreateRequest`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/apply` uses `NoteReplayActionRequest`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/approve` uses `NoteReplayActionRequest`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/reject` uses `NoteReplayActionRequest`
- `PATCH /api/v1/curation/entities/{entity_id}` uses `EntityUpdateRequest`
- `POST /api/v1/curation/entities/{entity_id}/aliases` uses `EntityAliasCreateRequest`
- `POST /api/v1/curation/entities/{entity_id}/relations` uses `EntityRelationUpsertRequest`
- `PATCH /api/v1/curation/entities/{entity_id}/relations/{relation_id}` uses `EntityRelationUpdateRequest`
- `PATCH /api/v1/curation/events/{event_id}` uses `EventUpdateRequest`
- `POST /api/v1/curation/events/{event_id}/participants` uses `EventParticipantUpsertRequest`
- `POST /api/v1/curation/events/{event_id}/relations` uses `EventRelationUpsertRequest`
- `PATCH /api/v1/curation/events/{event_id}/relations/{relation_id}` uses `EventRelationUpdateRequest`
- `POST /api/v1/review/merge-candidates/{candidate_id}/reject` uses `MergeCandidateRejectRequest`
- `POST /api/v1/review/merge-candidates/{candidate_id}/accept` uses `MergeCandidateAcceptRequest`
- `POST /api/v1/review/entities/{entity_id}/aliases` uses `ConfirmEntityAliasRequest`
- `POST /api/v1/image-generations` uses `ImageGenerationCreateRequest`
- `POST /api/v1/character-cards/from-entity/{entity_id}` uses `CharacterCardCreateRequest`
- `PATCH /api/v1/character-cards/{card_id}` uses `CharacterCardUpdateRequest`
- `POST /api/v1/character-cards/{card_id}/regenerate` uses `CharacterCardCreateRequest`
- `POST /api/v1/character-cards/{card_id}/generate-avatar` uses `CharacterCardAvatarGenerateRequest`
- `POST /api/v1/character-cards/{card_id}/generate-role-image` uses `CharacterCardRoleImageGenerateRequest`

Verification rule:

- `server/tests/api/test_openapi_contracts.py` should keep asserting these request bodies stay explicit and non-open-ended.

## Typed Read Response Contracts

The following read and replay surfaces now publish explicit response schemas through `response_model` declarations:

- `POST /api/v1/auth/login` returns `Envelope[TokenPayload]`
- `POST /api/v1/auth/logout` returns `Envelope[LogoutResponse]`
- `GET /api/v1/auth/me` returns `Envelope[CurrentUserResponse]`
- `POST /api/v1/assets/upload` returns `Envelope[AssetResponse]`
- `GET /api/v1/assets` returns `Envelope[PaginatedData[AssetResponse]]`
- `GET /api/v1/assets/{asset_id}` returns `Envelope[AssetDetailResponse]`
- `GET /api/v1/assets/{asset_id}/raw` returns `Envelope[AssetRawResponse]`
- `GET /api/v1/jobs` returns `Envelope[PaginatedData[JobResponse]]`
- `GET /api/v1/jobs/{job_id}` returns `Envelope[JobDetailResponse]`
- `POST /api/v1/jobs/{job_id}/retry` returns `Envelope[JobRetryResponse]`
- `GET /api/v1/entities` returns `Envelope[PaginatedData[EntityResponse]]`
- `GET /api/v1/entities/{entity_id}` returns `Envelope[EntityDetailResponse]`
- `GET /api/v1/entities/{entity_id}/events` returns `Envelope[EntityEventListResponse]`
- `GET /api/v1/events` returns `Envelope[PaginatedData[EventResponse]]`
- `GET /api/v1/events/{event_id}` returns `Envelope[EventDetailResponse]`
- `GET /api/v1/timeline` returns `Envelope[PaginatedData[TimelineItemResponse]]`
- `GET /api/v1/timeline/overview` returns `Envelope[TimelineOverviewResponse]`
- `GET /api/v1/timeline/range` returns `Envelope[TimelineRangeResponse]`
- `POST /api/v1/notes` returns `Envelope[NoteCreateResponse]`
- `GET /api/v1/notes` returns `Envelope[PaginatedData[NoteResponse]]`
- `GET /api/v1/notes/{note_id}` returns `Envelope[NoteResponse]`
- `GET /api/v1/notes/{note_id}/analysis-workflow` returns `Envelope[AnalysisWorkflowResponse]`
- `GET /api/v1/notes/{note_id}/extraction-runs` returns `Envelope[CollectionData[ExtractionRunResponse]]`
- `GET /api/v1/notes/{note_id}/extraction-runs/{run_id}` returns `Envelope[ExtractionRunResponse]`
- `GET /api/v1/notes/{note_id}/extraction-runs/compare` returns `Envelope[ExtractionRunCompareResponse]`
- `GET /api/v1/notes/{note_id}/replay-actions` returns `Envelope[CollectionData[ReplayActionResponse]]`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/apply` returns `Envelope[NoteExtractionRunApplyResponse]`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/approve` returns `Envelope[NoteExtractionRunApproveResponse]`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/reject` returns `Envelope[NoteExtractionRunRejectResponse]`
- `POST /api/v1/notes/{note_id}/reprocess` returns `Envelope[NoteCreateResponse]`
- `POST /api/v1/notes/{note_id}/story/regenerate` returns `Envelope[NoteStoryRegenerateResponse]`
- `GET /api/v1/views/story/note/{note_id}` returns `Envelope[StoryViewResponse]`
- `GET /api/v1/views/story/entity/{entity_id}` returns `Envelope[StoryViewResponse]`
- `GET /api/v1/search` returns `Envelope[SearchResultListResponse]`
- `GET /api/v1/search/unified` returns `Envelope[UnifiedSearchResponse]`
- `GET /api/v1/search/similar/{note_id}` returns `Envelope[SimilarNoteListResponse]`
- `GET /api/v1/search/merge-candidates` returns `Envelope[SearchMergeCandidateListResponse]`
- `GET /api/v1/review/merge-candidates` returns `Envelope[PaginatedData[MergeCandidateResponse]]`
- `GET /api/v1/review/merge-candidates/{candidate_id}` returns `Envelope[MergeCandidateDetailResponse]`
- `POST /api/v1/review/merge-candidates/{candidate_id}/reject` returns `Envelope[MergeCandidateRejectResponse]`
- `POST /api/v1/review/merge-candidates/{candidate_id}/accept` returns `Envelope[MergeCandidateAcceptResponse]`
- `GET /api/v1/review/entities/{entity_id}/context` returns `Envelope[EntityReviewContextResponse]`
- `POST /api/v1/review/entities/{entity_id}/aliases` returns `Envelope[ConfirmEntityAliasResponse]`
- `GET /api/v1/review/events/{event_id}/context` returns `Envelope[EventReviewContextResponse]`
- `GET /api/v1/curation/entities/{entity_id}` returns `Envelope[EntityCurationContextResponse]`
- `PATCH /api/v1/curation/entities/{entity_id}` returns `Envelope[EntityResponse]`
- `POST /api/v1/curation/entities/{entity_id}/aliases` returns `Envelope[EntityAliasResponse]`
- `DELETE /api/v1/curation/entities/{entity_id}/aliases/{alias_id}` returns `Envelope[EntityAliasRemovedResponse]`
- `POST /api/v1/curation/entities/{entity_id}/relations` returns `Envelope[CurationRelationItemResponse]`
- `PATCH /api/v1/curation/entities/{entity_id}/relations/{relation_id}` returns `Envelope[CurationRelationItemResponse]`
- `DELETE /api/v1/curation/entities/{entity_id}/relations/{relation_id}` returns `Envelope[RelationRemovedResponse]`
- `GET /api/v1/curation/events/{event_id}` returns `Envelope[EventCurationContextResponse]`
- `PATCH /api/v1/curation/events/{event_id}` returns `Envelope[EventCurationSubjectResponse]`
- `POST /api/v1/curation/events/{event_id}/participants` returns `Envelope[EventParticipantResponsePayload]`
- `DELETE /api/v1/curation/events/{event_id}/participants/{entity_id}` returns `Envelope[EventParticipantRemovedResponse]`
- `POST /api/v1/curation/events/{event_id}/relations` returns `Envelope[CurationRelationItemResponse]`
- `PATCH /api/v1/curation/events/{event_id}/relations/{relation_id}` returns `Envelope[CurationRelationItemResponse]`
- `DELETE /api/v1/curation/events/{event_id}/relations/{relation_id}` returns `Envelope[RelationRemovedResponse]`
- `GET /api/v1/graph/workspace` returns `Envelope[GraphWorkspaceResponse]`; supported query parameters are `event_id`, `entity_id`, `node_types`, `relation_types`, `start`, `end`, `min_weight`, and `depth`
- `GET /api/v1/graph/nodes/{node_type}/{node_id}` returns `Envelope[GraphWorkspaceNodeDetailResponse]`; it accepts the same graph scope/filter query parameters as `/graph/workspace`
- `GET /api/v1/operations/overview` returns `Envelope[OperationsOverviewResponse]`
- `POST /api/v1/image-generations` returns `Envelope[ImageGenerationCreateResponse]`
- `GET /api/v1/image-generations` returns `Envelope[PaginatedData[ImageGenerationResponse]]`
- `GET /api/v1/image-generations/{generation_id}` returns `Envelope[ImageGenerationResponse]`
- `POST /api/v1/character-cards/from-entity/{entity_id}` returns `Envelope[CharacterCardCreateResponse]`
- `GET /api/v1/character-cards` returns `Envelope[PaginatedData[CharacterCardResponse]]`
- `GET /api/v1/character-cards/{card_id}` returns `Envelope[CharacterCardResponse]`
- `PATCH /api/v1/character-cards/{card_id}` returns `Envelope[CharacterCardResponse]`
- `POST /api/v1/character-cards/{card_id}/regenerate` returns `Envelope[CharacterCardResponse]`
- `POST /api/v1/character-cards/{card_id}/generate-avatar` returns `Envelope[CharacterCardAvatarGenerateResponse]`
- `POST /api/v1/character-cards/{card_id}/generate-role-image` returns `Envelope[CharacterCardRoleImageGenerateResponse]`

Verification rules:

- `server/tests/api/test_openapi_contracts.py` should assert that these endpoints keep a component-backed response schema in `200` responses.
- paginated read models should continue using `data.items` as the primary collection field, with metadata in the same envelope.

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
- inspect derivative summaries and linked note refs from asset detail
- fetch raw material references
- proxy file uploads into MinIO from the API layer
- return original text or a presigned `raw_url` for raw reads

### Image Generations

- `POST /api/v1/image-generations`
- `GET /api/v1/image-generations`
- `GET /api/v1/image-generations/{generation_id}`

Responsibilities:

- create SyGPT-backed async image generation jobs
- accept prompt, model, aspect ratio, image size, and optional image reference asset ids
- preserve generation audit records separately from reusable raw image assets
- save completed generated images into MinIO and `raw_assets`
- expose generated asset ids and presigned raw URLs through the generation detail response

### Character Cards

- `POST /api/v1/character-cards/from-entity/{entity_id}`
- `GET /api/v1/character-cards`
- `GET /api/v1/character-cards/{card_id}`
- `PATCH /api/v1/character-cards/{card_id}`
- `POST /api/v1/character-cards/{card_id}/regenerate`
- `POST /api/v1/character-cards/{card_id}/generate-avatar`
- `POST /api/v1/character-cards/{card_id}/generate-role-image`
- `GET /api/v1/character-cards/{card_id}/avatar`
- `GET /api/v1/character-cards/{card_id}/role-image`
- `GET /api/v1/character-cards/{card_id}/export.json`

Responsibilities:

- turn entity story/detail data into editable SillyTavern `chara_card_v2` JSON
- preserve a source snapshot of the entity, timeline fragments, related events, and optional story view
- support faithful and creative regeneration modes
- generate avatar images through the async image generation pipeline and attach the first completed image asset to the card
- expose saved cards for editing and JSON export

### Notes

- `POST /api/v1/notes`
- `GET /api/v1/notes`
- `GET /api/v1/notes/{note_id}`
- `GET /api/v1/notes/{note_id}/analysis-workflow`
- `GET /api/v1/notes/{note_id}/extraction-runs`
- `GET /api/v1/notes/{note_id}/extraction-runs/{run_id}`
- `GET /api/v1/notes/{note_id}/extraction-runs/compare?base_run_id=...&candidate_run_id=...`
- `GET /api/v1/notes/{note_id}/replay-actions`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/approve`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/reject`
- `POST /api/v1/notes/{note_id}/extraction-runs/{run_id}/apply`
- `POST /api/v1/notes/{note_id}/reprocess`
- `POST /api/v1/notes/{note_id}/story/regenerate`

Responsibilities:

- create knowledge entries from assets
- read note summaries and canonical text
- expose the full read-only analysis chain for a note: raw asset, derivatives, jobs, extraction runs, projection versions, and replay audit actions
- trigger async reprocessing
- preserve extraction history through `extraction_runs`
- expose extraction run version metadata such as provider, model, prompt, schema, input hash, run kind, and projection status
- expose note-level analysis workflow evidence groups through `evidence_groups`, including target type/id, field names, evidence count, average confidence, and source snippet samples
- expose active-run raw-output versus normalized-output comparison through `raw_normalized_diff`
- expose extraction run history, run summaries, and side-by-side diff snapshots
- create `ready_for_review` draft runs during reprocess when an active projection already exists
- approve or reject reviewable draft runs explicitly before changing the current projection
- apply a selected historical extraction run back into the current note projection
- regenerate the note-level story view from the currently applied extraction run's `style_payload`
- expose replay audit history for automatic and manual projection-apply actions, including projection-version ids
- expose replay audit history for story-view regeneration actions
- return the active note projection pointer and the projection version id created by apply/approve actions
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
- return payload and result details from single-job inspection
- expose paginated job history for inbox and retry UIs

### Operations

- `GET /api/v1/operations/overview`

Responsibilities:

- aggregate failed-job alerts, raw asset type counts, extraction-review backlog, merge-candidate backlog, and recent operator actions
- provide operator-routing links into note detail, review, and curation pages
- keep the operations console from stitching together unrelated list endpoints for top-level health signals

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
