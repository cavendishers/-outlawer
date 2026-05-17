# Development Phases

## How To Use This Document

- each phase has a manual status section
- when a phase starts, change its status to `IN_PROGRESS`
- when a phase is done and verified, change its status to `DONE`
- after marking a phase complete, update the related documents listed in that phase

Status values to use:

- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

## Latest Verification

Verified on `2026-04-21` in Docker using [`server/scripts/e2e_api_flow.py`](/Users/hongan/Documents/fxxk/server/scripts/e2e_api_flow.py).

- `python3 -m compileall server/app` -> passed
- `python3 server/scripts/e2e_api_flow.py --phase phase1` -> passed
- `python3 server/scripts/e2e_api_flow.py --phase phase2` -> passed
- `python3 server/scripts/e2e_api_flow.py --phase phase3` -> passed
- `python3 server/scripts/e2e_api_flow.py --phase full` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml up migrate --build` -> applied `20260418_02_entity_seen_timestamps`
- `docker compose -f deploy/compose/docker-compose.prod.yml config` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed
- `docker compose -p phase9check -f deploy/compose/docker-compose.prod.yml up -d postgres rabbitmq redis minio migrate` -> migration succeeded in clean volumes
- OpenRouter free-model fallback was verified with `python3 server/scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240`
- OpenRouter text extraction persistence was verified in Docker with completed `ai_jobs`, `relations`, `events.location_text`, and `merge_candidates` records
- multimodal ingest smoke verification passed for image, audio, and video uploads with locally generated derivative text persisted through `asset_derivatives.normalized_text`
- local OCR and ASR fallback was verified in Docker after rebuilding `api` and `worker` with `ffmpeg`, `tesseract`, and `vosk`
- `curl -I http://localhost:3000` -> `200 OK`
- `python3 -m compileall server/app server/tests server/scripts` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_entity_curation_flow.py` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/integration/test_e2e_entity_curation_flow.py` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_curation_flow.py` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/integration/test_e2e_curation_flow.py tests/integration/test_e2e_entity_curation_flow.py` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extraction_run_service.py tests/services/test_asset_text_service.py tests/services/test_local_media_service.py` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py tests/api/test_health.py` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py` -> passed with search, review, and curation response-contract coverage
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed with extraction reprocess draft approval, rejection, historical replay, image semantic derivative verification, audio context derivative verification, and operations API detail verification
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api alembic upgrade head` -> passed with migration `20260420_04_source_of_truth_cleanup`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py` -> passed after Phase A source-of-truth cleanup
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase A source-of-truth cleanup
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api alembic upgrade head` -> passed with migration `20260421_05_extraction_projection_versioning`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extraction_run_service.py tests/api/test_openapi_contracts.py` -> passed after Phase B extraction/projection versioning
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed after Phase B extraction/projection versioning
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase B extraction/projection versioning
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extraction_run_service.py tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 1
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed after Phase C domain packaging slice 1
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 1
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extraction_run_service.py tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 2
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 2
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extractor_service.py tests/services/test_extraction_run_service.py` -> passed after Phase C domain packaging slice 3
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 3
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_projection_service.py tests/services/test_extractor_service.py tests/services/test_extraction_run_service.py` -> passed after Phase C domain packaging slice 4
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 4
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py tests/services/test_projection_service.py tests/services/test_extractor_service.py tests/services/test_extraction_run_service.py` -> passed after Phase C domain packaging slice 5
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 5
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py tests/integration/test_e2e_curation_flow.py tests/integration/test_e2e_entity_curation_flow.py` -> passed after Phase C domain packaging slice 6
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_review_flow.py` -> passed after Phase C domain packaging slice 6
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_curation_flow.py` -> passed after Phase C domain packaging slice 6
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_entity_curation_flow.py` -> passed after Phase C domain packaging slice 6
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 6
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_graph_service.py tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 7
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 7
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 8
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 8
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 9
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 9
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_asset_text_service.py tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 10
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 10
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extractor_service.py tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 11
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 11
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_local_media_service.py tests/services/test_asset_text_service.py tests/services/test_extractor_service.py` -> passed after Phase C domain packaging slice 12
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 12
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_local_media_service.py tests/services/test_asset_text_service.py tests/services/test_extractor_service.py tests/api/test_openapi_contracts.py` -> passed after Phase C domain packaging slice 13
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Phase C domain packaging slice 13

## Architecture Blueprint Track

### Phase A: Source-of-truth cleanup

Status: `DONE`

Verified on `2026-04-21`

Work items:

- move canonical alias writes and reads to `entity_aliases`
- centralize note, entity, and event vectors in `embeddings`
- remove `note_chunks.embedding_vector`
- stop duplicating canonical participant facts into `relations(participates_in)`
- add uniqueness constraints for alias, participant, and embedding truth boundaries

Completion criteria:

- alias governance and read models query `entity_aliases`
- vector writes use `embeddings` only
- `event_entities` remains the canonical participant fact store
- migration applies cleanly and e2e flow stays green

Documents updated after completion:

- `README.md`
- `docs/architecture-v2-blueprint.md`
- `docs/current-system-overview.md`
- `docs/database-design.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

### Phase B: Extraction/projection versioning

Status: `DONE`

Verified on `2026-04-21`

Work items:

- enrich `extraction_runs` with provider/model/prompt/schema/input lineage metadata
- add a shared extraction metadata registry helper
- add immutable `projection_versions`
- add `notes.active_projection_id` as the active projection pointer
- record projection-version ids in replay and approval audit payloads

Completion criteria:

- extraction history is version-aware instead of only status-aware
- every apply/approve path writes an immutable projection version record
- the active note projection is explicit through a pointer rather than inferred only from run status
- migration applies cleanly and replay e2e remains green

Documents updated after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/architecture-v2-blueprint.md`
- `docs/current-system-overview.md`
- `docs/database-design.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

### Phase C: Domain packaging

Status: `DONE`

Verified on `2026-04-21`

Work items:

- reorganize backend into domain-first modules under `server/app/domains`
- keep route and task layers thin by importing through domain boundaries
- split extraction and replay logic out of oversized horizontal services
- preserve compatibility shims while the packaging migration is still underway

Delivered in slice 1:

- introduced `app.domains.extraction` and `app.domains.replay` packages
- moved extraction metadata registry helpers into `app.domains.extraction.metadata`
- moved worker pipeline orchestration into `app.domains.extraction.pipeline`
- moved replay diff and payload-summary logic into `app.domains.replay.diff`
- updated note API, worker task, query service, and tests to import through the new domain seams
- kept `app.services.extraction_metadata_service` and `app.services.pipeline_service` as compatibility re-export shims during the transition
- reduced `app.services.extraction_run_service` substantially by extracting diff helpers into the replay domain package

Delivered in slice 2:

- moved the replay service implementation itself into `app.domains.replay.service`
- reduced `app.services.extraction_run_service` to a compatibility shim that re-exports the domain implementation
- kept note API, worker pipeline, and replay tests green while the implementation moved behind the new domain boundary

Delivered in slice 3:

- moved extraction payload orchestration and merge heuristics into `app.domains.extraction.extractor`
- updated the extraction pipeline and extractor service tests to depend on the new extraction domain path
- reduced `app.services.extractor_service` to a compatibility shim for legacy imports

Delivered in slice 4:

- moved projection persistence and read/write helpers into `app.domains.projection.service`
- updated replay and extraction pipelines to depend on the projection domain path directly
- reduced `app.services.projection_service` to a compatibility shim for legacy imports

Delivered in slice 5:

- moved note, entity, event, and timeline query services into `app.domains.retrieval.*`
- updated API routes and key read-side callers to depend on the retrieval domain path directly
- reduced the old query service modules to compatibility shims while the migration continues

Delivered in slice 6:

- moved merge review, alias confirmation, event/entity curation, and governance object-summary helpers into `app.domains.governance.review` and `app.domains.governance.curation`
- updated review, curation, and operations callers to import the governance domain path directly
- reduced `app.services.review_service` and `app.services.curation_service` to compatibility shims while the migration continues
- hardened entity/event merge rewrites so duplicate alias and participant conflicts are resolved before flush, keeping governance e2e green during the packaging move

Delivered in slice 7:

- moved graph overview, related-event suggestion, and entity timeline fragment read models into `app.domains.retrieval.graph_query`
- moved graph workspace composition into `app.domains.retrieval.graph_workspace`
- updated graph API routes, retrieval queries, governance readers, and graph service tests to import the retrieval domain paths directly
- reduced `app.services.graph_service` and `app.services.graph_workspace_service` to compatibility shims while graph read models finish migrating

Delivered in slice 8:

- moved note/entity/event/similar unified search composition into `app.domains.retrieval.search_query`
- moved `/search/unified` and `/search/similar` payload assembly out of the route layer and into the retrieval domain
- reduced `app.services.search_service` to a compatibility shim while remaining callers migrate
- kept search, graph, and broader API Docker e2e green after the search read model joined the retrieval domain

Delivered in slice 9:

- introduced `app.domains.operations`
- moved operations overview/backlog/activity aggregation into `app.domains.operations.overview`
- updated operations API routes to depend on the operations domain path directly
- reduced `app.services.operations_service` to a compatibility shim while operations read models finish migrating

Delivered in slice 10:

- moved raw-asset text preparation, multimodal derivative normalization, and derivative upsert helpers into `app.domains.extraction.asset_text`
- updated notes API, extraction pipeline, and asset-text tests to depend on the extraction domain path directly
- reduced `app.services.asset_text_service` to a compatibility shim while remaining callers migrate

Delivered in slice 11:

- moved OpenRouter extraction and multimodal request helpers into `app.domains.extraction.openrouter`
- updated extraction payload building, asset-text preparation, and extractor tests to depend on the extraction domain path directly
- reduced `app.services.openrouter_service` to a compatibility shim while remaining callers migrate

Delivered in slice 12:

- moved local OCR/ASR/video frame parsing helpers into `app.domains.extraction.local_media`
- updated asset-text preparation and local media tests to depend on the extraction domain path directly
- reduced `app.services.local_media_service` to a compatibility shim while remaining callers migrate

Delivered in slice 13:

- introduced `app.domains.knowledge`
- moved canonical alias helpers into `app.domains.knowledge.aliases`
- moved embedding upsert helpers into `app.domains.knowledge.embeddings`
- updated retrieval, governance, and projection domain modules to depend on the knowledge domain paths directly
- reduced `app.services.entity_alias_service` and `app.services.embedding_service` to compatibility shims while remaining callers migrate

Completion criteria:

- extraction, projection, replay, and read concerns no longer accumulate in a single horizontal `services` bucket
- route handlers and worker entrypoints depend on domain packages rather than implementation-heavy service modules
- compatibility shims can eventually be removed without changing public API behavior
- Docker verification and full API e2e remain green after each packaging slice

Documents updated after this slice:

- `README.md`
- `docs/architecture-v2-blueprint.md`
- `docs/current-system-overview.md`
- `docs/development-phases.md`
- `docs/remaining-features-roadmap.md`

## Phase 0: Foundation and Conventions

Status: `DONE`

Goal:

- establish repository structure, documentation baseline, and engineering rules

Work items:

- create `web/`, `server/`, and `deploy/`
- initialize README, AGENTS, and core docs
- finalize architecture, API, database, deployment, and migration rules

Completion criteria:

- repo structure exists
- docs baseline exists
- development and migration rules are agreed

Documents to update manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/development-phases.md`

## Phase 1: Backend Bootstrap and Auth

Status: `DONE`

Goal:

- establish FastAPI foundation and username/password login

Work items:

- initialize FastAPI app structure
- add config, logging, database session management, and health endpoints
- create `users` model and first Alembic migration
- implement password hashing and JWT auth
- add `auth/login`, `auth/logout`, and `auth/me`
- add initial backend tests

Completion criteria:

- FastAPI app boots inside Docker
- login flow works
- first migration applies cleanly

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/migration-guide.md`
- `docs/development-phases.md`

## Phase 2: Raw Asset Ingestion

Status: `DONE`

Goal:

- support text, image, audio, and video input with raw asset persistence

Work items:

- integrate MinIO client
- create `raw_assets` and `asset_derivatives` migrations
- add asset upload API
- support original text storage
- store file metadata and object keys
- persist normalized derivative text for multimodal assets
- add local OCR and ASR fallback for image, audio, and video parsing
- add asset listing and detail APIs

Completion criteria:

- raw assets are stored safely
- metadata can be queried
- original text and file-based assets are both supported
- image, audio, and video uploads can generate derivative text for downstream extraction

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/deployment.md`
- `docs/development-phases.md`

## Phase 3: Async Pipeline and Job Tracking

Status: `DONE`

Goal:

- introduce Celery, RabbitMQ, and tracked async processing

Work items:

- configure Celery app
- connect RabbitMQ broker
- add `ai_jobs` migration and job repository/service
- create worker container and task queue wiring
- add job status and retry APIs

Completion criteria:

- jobs can be enqueued and consumed
- job status is queryable
- failed jobs can be retried

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/deployment.md`
- `docs/migration-guide.md`
- `docs/development-phases.md`

## Phase 4: Note Canonicalization and Extraction Persistence

Status: `DONE`

Goal:

- create notes and persist extraction results safely

Work items:

- create `notes`, `note_chunks`, and `extraction_runs`
- implement note creation from asset
- persist raw extraction JSON
- normalize extraction results before final writes
- add reprocess endpoint

Completion criteria:

- note creation starts async processing
- extraction results are stored and replayable
- reprocessing flow exists

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/ai-extraction-format.md`
- `docs/development-phases.md`

## Phase 5: Entity, Event, Relation, and Timeline Graph

Status: `DONE`

Goal:

- implement the knowledge graph core

Work items:

- create `entities`, `events`, `event_entities`, `relations`, `note_entities`, `note_events`, `timeline_items`, and `extraction_evidence`
- implement entity extraction and event extraction persistence
- implement event-centric relation building
- implement timeline projection generation
- build entity, event, and timeline query APIs

Completion criteria:

- people index can be built from stored entities
- event pages can show linked entities
- timeline is queryable from projection data

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/ai-extraction-format.md`
- `docs/development-phases.md`

## Phase 6: Search, Embeddings, and Merge Candidates

Status: `DONE`

Goal:

- add similarity recall and duplicate candidate workflows

Work items:

- create `embeddings` and `merge_candidates`
- generate note, chunk, entity, or event embeddings
- add similarity search endpoint
- generate duplicate candidates for entity and event review

Completion criteria:

- similar content can be queried
- merge candidates are persisted for later review

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/migration-guide.md`
- `docs/development-phases.md`

## Phase 7: Stylized Story Views

Status: `DONE`

Goal:

- turn structured knowledge into stylized presentation views

Work items:

- create `style_views`
- implement structured `style_payload` handling
- generate chunibyo-style note and entity story views
- add story view APIs

Completion criteria:

- note and entity story views are queryable
- stylized output remains separate from canonical knowledge

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/ai-extraction-format.md`
- `docs/development-phases.md`

## Phase 8: Frontend MVP

Status: `DONE`

Goal:

- build the first usable product surface

Work items:

- initialize Next.js app
- add login page
- add inbox and library pages
- add note detail page
- add people page
- add events page
- add timeline page
- add story view pages

Completion criteria:

- the MVP flow works end to end in Docker
- user can log in, upload content, wait for processing, and browse results

Documents to update manually after completion:

- `README.md`
- `docs/architecture.md`
- `docs/api-contract.md`
- `docs/deployment.md`
- `docs/development-phases.md`

## Phase 9: Hardening and Release Readiness

Status: `DONE`

Goal:

- make the system maintainable and release-ready

Work items:

- improve test coverage
- validate migration workflow in clean environments
- add better logging and failure visibility
- document backup, restore, and operational steps
- validate production compose setup

Current verified progress:

- pytest regression suite added for health, extractor behavior, and full API flow
- API request logging with request IDs is active
- worker task lifecycle logging is active after worker restart
- production compose file now validates with `docker compose ... config`
- backup and restore runbook exists in `docs/operations.md`

Completion criteria:

- core flows are covered by tests
- deployment steps are documented and repeatable
- release checklist exists

Documents to update manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/deployment.md`
- `docs/migration-guide.md`
- `docs/development-phases.md`

## Phase 10: Architecture Hardening And Contract Cleanup

Status: `DONE`

Goal:

- reduce future feature cost by hardening internal boundaries and public API conventions

Work items:

- introduce shared pagination and response helpers
- centralize repeated API serialization logic
- move search aggregation into a dedicated service
- introduce generic job dispatch entry points
- correct graph-facing timestamp modeling issues
- produce an architecture review and iteration plan

Completion criteria:

- key list endpoints return consistent pagination metadata
- route files are thinner and rely more on services/helpers
- at least one schema-level modeling issue is corrected through migration
- architecture review and target direction are documented

Documents to update manually after completion:

- `README.md`
- `docs/architecture.md`
- `docs/architecture-review.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/development-phases.md`

## Phase 11: Entity And Event Review Workflow

Status: `DONE`

Goal:

- add the first operational review workflow so extracted entities and events can be accepted, rejected, merged, and audited

Work items:

- add review queue APIs
- add accept and reject review actions
- implement entity merge and event merge logic
- add alias confirmation support
- add review audit logging
- build review queue and review context pages
- add phase-specific e2e validation

Completion criteria:

- merge candidates can be reviewed in API and web UI
- accepted merges update dependent graph records consistently
- rejected candidates remain auditable
- review workflow is covered by e2e

Implementation notes:

- review queue APIs are live under `/api/v1/review`
- entity merge, event merge, alias confirmation, and audit logging are implemented
- web review pages are available at `/review`, `/review/entities/[id]`, and `/review/events/[id]`
- verification now includes `server/scripts/e2e_review_flow.py` in addition to the existing full API e2e

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/development-phases.md`
- `docs/phase-11-review-workflow-plan.md`

## Phase 12: Event Curation And Graph Editing Slice

Status: `DONE`

Goal:

- add the first manual graph curation workflow so events can be corrected and graph links can be maintained without re-running extraction

Work items:

- add event curation context API
- add event field update API
- add participant add/remove APIs
- add relation add/remove APIs for event-centered graph maintenance
- build event curation page in the web app
- add phase-specific e2e validation

Completion criteria:

- an event can be manually corrected in the UI and API
- participant changes update graph join data consistently
- relation changes are reflected in the curation context
- timeline projection stays aligned with edited event fields
- curation workflow is covered by e2e

Documents to update manually after completion:

- `README.md`
- `docs/api-contract.md`
- `docs/database-design.md`
- `docs/development-phases.md`
- `docs/remaining-features-roadmap.md`
- `docs/phase-12-event-curation-plan.md`

## Phase 13: Entity Curation And Alias Governance

Status: `DONE`

Goal:

- add the second manual graph curation workflow so person/entity records can be corrected without rerunning extraction

Work items:

- add entity curation context API
- add entity field update API
- add trusted alias add/remove APIs
- build entity curation page in the web app
- link story and review entry points into the entity curation workflow
- add phase-specific e2e validation

Completion criteria:

- an entity can be manually corrected in the UI and API
- alias governance updates entity search/display data consistently
- story and review pages can route into the entity curation workflow
- entity curation workflow is covered by e2e

Documents to update manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 14: Relation Governance And Entity-Centered Graph Editing

Status: `DONE`

Goal:

- let curated graph relations be edited in place and maintained from both event and entity entry points

Work items:

- add shared relation update service logic for curation workflows
- add entity-centered relation add/update/remove APIs
- add event relation update API
- extend event and entity curation pages with relation edit-in-place interactions
- add phase-specific e2e validation for relation editing

Completion criteria:

- event curation can edit an existing relation without deleting and recreating it manually
- entity curation can add, edit, and remove graph relations
- participant links remain governed separately from generic relation editing
- relation governance is covered by e2e

Documents to update manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 15: Multimodal Quality Upgrade Slice 1

Status: `DONE`

Goal:

- improve multimodal derivative quality without changing the storage model by combining local parsing, optional AI enrichment, and source attribution

Work items:

- stop short-circuiting multimodal enrichment after the first successful local parser result
- merge local multimodal observations with OpenRouter multimodal output when available
- preserve source attribution snippets from OCR and ASR segments
- enrich canonical multimodal text with confidence and source-fragment sections
- add service-level regression tests for multimodal payload merging

Completion criteria:

- multimodal assets can retain local OCR/ASR observations even when AI enhancement also runs
- normalized derivative text carries richer attribution and observation context
- the multimodal merge behavior is covered by automated tests

Documents to update manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 16: Multimodal Video Scene Evidence Attribution

Status: `DONE`

Goal:

- make video-derived knowledge more trustworthy by separating sampled scene evidence from model inference

Work items:

- sample video frames according to media duration instead of using a fixed frame count
- attach timecodes and scene labels to local video frame OCR evidence
- add `video_scene_segments` to multimodal derivative payloads
- normalize `evidence_type` values for direct observation, model inference, and mixed evidence
- update OpenRouter multimodal prompts to return the same attribution structure
- render video scene evidence inside canonical derivative text
- add service-level regression tests for scene segments and evidence typing

Completion criteria:

- video derivatives can preserve sampled scene time ranges for later extraction and review
- canonical derivative text clearly labels direct evidence versus model inference
- local and OpenRouter multimodal payloads can merge scene segments without losing attribution
- service-level tests cover the evidence attribution behavior

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 17: Extraction Run History And Diff Review Slice

Status: `DONE`

Goal:

- make reprocessing safer by exposing extraction run history and side-by-side diff review before later replay controls are added

Work items:

- add note-scoped extraction run list and detail APIs
- add note-scoped extraction run compare API
- normalize extraction payloads into stable diff sections for summary, entities, events, relations, similarity hints, and style payloads
- surface recent extraction run history and latest diff snapshot in the note detail page
- extend service tests and full API e2e coverage for extraction history and compare flows

Completion criteria:

- a note exposes its extraction run history through the API
- any two extraction runs for the same note can be compared through a stable diff payload
- the note detail page can display recent run metadata and a latest diff snapshot
- automated verification covers diff logic and note-scoped extraction run APIs

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 18: Projection Replay And Historical Run Apply Slice

Status: `DONE`

Goal:

- let a user explicitly re-apply a stored extraction run so current projections can be rolled back or replayed without rerunning the model immediately

Work items:

- add note-scoped apply endpoint for a historical extraction run
- track applied versus superseded extraction run state within existing run records
- reuse stored normalized extraction payloads to rebuild the canonical note projection
- surface current-applied state and rollback action in the note detail page
- extend full API e2e to cover reprocess plus historical run re-apply

Completion criteria:

- a saved extraction run can be applied back onto the current note projection
- note-scoped extraction runs clearly indicate which run is currently applied
- the note detail page can trigger a rollback/replay action against an existing run
- automated verification covers apply and status transitions for extraction runs

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 19: Replay Audit Trail And Operator Note Slice

Status: `DONE`

Goal:

- make projection replay actions auditable by recording both automatic and manual apply actions with optional operator notes

Work items:

- log automatic extraction-run apply actions into `review_actions`
- log manual historical run apply actions with optional operator notes
- add note-scoped replay action list API
- surface replay audit history and operator note input in the note detail page
- extend full API e2e to verify replay audit persistence

Completion criteria:

- both automatic and manual projection applies are queryable through a note-scoped audit log
- manual replay apply can store an operator note for later review
- the note detail page can show replay action history beside run history and diffs
- automated verification covers replay action log writes and reads

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 20: Draft Replay Approval Flow

Status: `DONE`

Goal:

- make reprocess safe by generating a reviewable extraction draft before any new projection is applied

Work items:

- make note reprocess create a `ready_for_review` extraction run instead of auto-applying it
- keep the active projection unchanged until explicit approval
- add explicit approve and reject endpoints for reviewable extraction runs
- record approve and reject actions in replay audit history
- update note detail to distinguish active, draft-review, rejected, and historical runs
- extend full API e2e for draft creation, approval, rejection, and projection preservation

Completion criteria:

- reprocess no longer overwrites the current projection automatically
- a draft extraction run can be approved or rejected explicitly
- note detail can show and act on pending review candidates separately from rollback history
- automated verification covers draft replay approval and rejection flows

Documents to update manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/development-phases.md`

## Phase 21: Image Semantic Enrichment

Status: `DONE`

Goal:

- improve image ingestion quality by preserving structured semantic hints beyond OCR-only text

Work items:

- add local image semantic fallback fields for likely scene, visible objects, likely actions, document/photo type, and image layout
- allow image derivatives to be generated even when OCR text is empty, using title and image metadata as conservative hints
- extend OpenRouter multimodal prompts to request the same image semantic fields
- merge image semantic fields into `analysis_json`, `normalized_text`, and canonical multimodal text
- extend full API e2e to verify image upload through derived semantic payloads

Completion criteria:

- image assets can produce useful derivative text even when OCR is unavailable or empty
- image semantic fields are queryable from `asset_derivatives.analysis_json`
- normalized derivative text includes scene, object, action, document-type, and layout sections
- automated verification covers service-level merging and full image upload-to-derivative flow

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/database-design.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/development-phases.md`

## Phase 22: Audio Speaker And Context Enrichment

Status: `DONE`

Goal:

- improve audio ingestion quality by preserving conversation context and transcript segments beyond flat ASR text

Work items:

- add local audio context fallback fields for conversation type, speaker hints, topics, decisions, and follow-ups
- build time-ordered audio transcript segments when ASR word timing is available
- allow audio derivatives to be generated even when transcript text is empty, using title-level context as conservative hints
- extend OpenRouter multimodal prompts to request the same audio context and segment fields
- merge audio context fields into `analysis_json`, `normalized_text`, and canonical multimodal text
- extend full API e2e to verify audio upload through derived semantic payloads

Completion criteria:

- audio assets can produce useful derivative text even when ASR transcript is unavailable or empty
- audio context fields are queryable from `asset_derivatives.analysis_json`
- normalized derivative text includes conversation type, topics, follow-ups, and transcript segment sections when available
- automated verification covers service-level merging and full audio upload-to-derivative flow

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/database-design.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/development-phases.md`

## Phase 23: Operations Dashboard Foundation

Status: `DONE`

Goal:

- provide an operator-facing page for jobs, retries, raw assets, derivative summaries, and extraction-run inspection

Work items:

- build a dedicated operations page in the web app
- expose job payload/result inspection for runtime debugging
- expose asset derivative summaries and linked note refs from asset detail
- allow failed jobs to be retried directly from the operations page
- show note extraction runs from an operator-oriented dashboard entry point

Completion criteria:

- operators can inspect recent jobs and retry failed jobs without leaving the product
- operators can inspect raw assets together with derivative summaries from the product surface
- operators can inspect extraction runs for recent notes from the operations page
- automated verification covers the API detail shapes used by the operations console

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/development-phases.md`

## Phase 24: Strongly Typed API Contracts

Status: `DONE`

Goal:

- replace open-ended request dictionaries on core write APIs with explicit Pydantic contracts

Work items:

- type note create and extraction replay write requests
- type merge review and alias confirmation write requests
- type entity/event curation write requests
- add OpenAPI contract tests that lock request bodies to explicit schemas

Completion criteria:

- core note, review, and curation write endpoints no longer accept generic `dict` payloads
- OpenAPI publishes explicit request body schemas for those endpoints
- automated verification proves the existing review and curation flows still work end to end

Follow-up note:

- `2026-04-20`: core auth, asset, job, note, entity, event, timeline, and story-view read endpoints were further hardened with explicit `response_model` contracts and OpenAPI response tests.
- `2026-04-20`: search, review, and curation response contracts were also hardened so the main public API surfaces now expose explicit OpenAPI response schemas end to end.

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/development-phases.md`

## Phase 25: Query Service Layer For Read Models

Status: `DONE`

Goal:

- move the main browse/detail read assembly out of route files and into dedicated query services

Work items:

- extract note read queries into a dedicated query service
- extract entity read queries into a dedicated query service
- extract event read queries into a dedicated query service
- extract timeline read queries into a dedicated query service
- reuse shared read helpers from review and curation where it reduces duplicated composition logic

Completion criteria:

- note, entity, event, and timeline routes no longer assemble their main read payloads inline
- core browse/detail response shapes stay stable for the frontend
- automated verification proves review and curation flows still work after the read-side refactor

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/current-system-overview.md`
- `docs/remaining-features-roadmap.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/development-phases.md`

## Phase 26: Graph Workspace And Canvas Editing

Status: `IN_PROGRESS`

Goal:

- evolve graph browsing and correction from form-driven pages into a stronger graph workspace

Execution plan:

- detailed implementation plan is tracked in `docs/phase-26-graph-workspace-plan.md`
- Phase 26 should be delivered in slices rather than one large graph rewrite
- each slice should preserve the existing review and curation governance flow

Current slice delivered:

- event detail page now includes an association workspace with an anchor event panel, vertical related-event rail, and focused node inspector
- entity story page now includes a timeline workspace with fragment stepping, previous/next context, and side-axis event echoes
- graph-first navigation shortcuts now connect event and entity workspaces back to review and curation flows
- shared `/graph` route now provides one unified graph workspace shell
- `/api/v1/graph/workspace` now provides event-anchored, entity-anchored, and overview workspace payloads
- event detail page, entity story page, and timeline page now expose direct entry links into the shared graph workspace
- `/api/v1/graph/nodes/{node_type}/{node_id}` now provides node-detail neighborhoods for the shared inspector
- shared graph workspace now keeps `active_node_id` in the URL and supports connected-node plus timeline-context navigation in-place
- shared graph workspace now supports inline event participant edits plus event/entity relation add, update, and remove directly in the node inspector
- inline graph edits now refresh the current workspace locally after each successful mutation and still preserve links to the full curation pages
- shared graph workspace now includes `全部 / 事件 / 人物 / 时间主干` viewing modes
- timeline backbone rail can now select visible event nodes directly inside the shared workspace instead of always leaving for detail pages
- shared graph workspace now has skeleton loading states, a dedicated empty state, stronger active-node emphasis, and clearer inline validation feedback
- shared graph workspace now lets visible edges be focused directly, with an edge spotlight rail and quick pivot actions to either endpoint

Remaining work:

- continue pushing graph editing toward a broader canvas-native experience after UX hardening

Recommended next slices:

- Slice A: shared `/graph` route and workspace shell
- Slice B: shared inspector and node-focused navigation
- Slice C: inline relation and participant editing
- Slice D: timeline backbone fused into the shared workspace
- Slice E: mobile, loading, and UX hardening
- Slice F: broader canvas-native graph editing, if graph depth becomes the next priority again

Phase 26 documents to update manually as work proceeds:

- `README.md`
- `docs/current-system-overview.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/remaining-features-roadmap.md`
- `docs/phase-26-graph-workspace-plan.md`
- `docs/development-phases.md`

Verification completed for current slice:

- `npm run build` in `web/`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m compileall app`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_health.py tests/integration/test_e2e_api_flow.py tests/integration/test_e2e_review_flow.py tests/integration/test_e2e_curation_flow.py tests/integration/test_e2e_entity_curation_flow.py`

Slice A follow-up verification:

- `python3 -m compileall server/app server/tests web/app web/components web/lib` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py` -> passed
- `cd web && npx tsc --noEmit` -> passed
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed with graph node detail coverage
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed after wrapping `/graph` search-param reads in a Suspense-backed client boundary
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after inline graph edit integration
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed with inline graph governance rail enabled
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after timeline backbone fusion
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed with timeline backbone rail and workspace view filters enabled
- `cd web && npx tsc --noEmit` -> passed after Slice E UX hardening
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed after Slice E UX hardening
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after Slice E UX hardening
- `cd web && npx tsc --noEmit` -> passed after edge spotlight graph iteration
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'` -> passed after edge spotlight graph iteration
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240` -> passed after edge spotlight graph iteration

## Phase 27: Operations Console Deepening

Status: `DONE`

Goal:

- turn the first operations page from a recent-list dashboard into a backlog-oriented operator console

Work items:

- add a dedicated `/api/v1/operations/overview` read endpoint for top-level operational signals
- surface failed jobs, extraction-review backlog, merge-candidate backlog, asset type distribution, and recent operator activity in the web console
- route operators directly from global signals into note detail, review, and curation pages
- keep the new operations read model explicit in OpenAPI and covered by API e2e

Completion criteria:

- operators can see the main backlog and failure signals without stitching multiple list views together mentally
- the operations console can route directly into the most relevant action pages
- OpenAPI publishes an explicit response model for the new operations overview endpoint
- full API e2e verifies the new operations overview surface

Documents updated manually after completion:

- `README.md`
- `AGENTS.md`
- `docs/api-contract.md`
- `docs/current-system-overview.md`
- `docs/operations.md`
- `docs/remaining-features-roadmap.md`
- `docs/project-retrospective-and-next-stage.md`
- `docs/development-phases.md`

Verification completed for current slice:

- `cd web && npx tsc --noEmit`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240`

## Phase 28: UI System Consolidation

Status: `IN_PROGRESS`

Goal:

- preserve the strong Outlawer brutalist identity while making deep product pages easier to scan and read

Work items:

- extend visual tokens with quiet surfaces, canvas surfaces, muted text, and softer shadow levels
- formalize reusable hierarchy classes for page headers, body copy, dossier cards, metric cards, graph canvases, and graph nodes
- reduce overuse of `neon` and `font-black` on deep pages
- refactor core pages and graph components toward stable color responsibilities and responsive graph fallbacks
- document the UI token contract in `docs/visual-tokens.md`

Completion criteria:

- homepage keeps the strong visual direction
- people, event, library, search, timeline, story, and graph-heavy views have clearer hierarchy
- mobile graph-related views have readable list alternatives where horizontal canvas would be fragile
- frontend typecheck and production build pass

Documents to update manually after completion:

- `docs/visual-tokens.md`
- `docs/development-phases.md`

Verification planned for current slice:

Verification completed for current slice:

- `cd web && npx tsc --noEmit`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'`
- browser smoke on `/`, `/people`, `/events`, `/timeline`, `/search`

Verification note:

- browser smoke ran with an expired local auth token, so protected list data did not render; the smoke still confirmed page rendering and no horizontal overflow on the checked routes
- follow-up visual correction removed the dossier-card left black rail and restored full hard nav/card shadows after review on the event list screenshot
- `/events` was promoted into the first list-page sample: short task-bar hero, event count stamp, and time-anchor event cards that make the records the visual focus
- `/events` follow-up removed decorative English labels and reduced work-page title/card typography to avoid homepage-scale poster sizing on dense lists
- `/events` title hierarchy was corrected so Chinese page titles use stable heavy body typography instead of the weaker display font, with card titles kept one level lower
- `/events` was compressed into a higher-density work list: compact header, small tool actions, one-line summaries, and explained confidence chips instead of standalone percentage badges
- global navigation was compressed into three primary links plus `知识库` and `更多` menus to reduce flat navigation overload
- workbench list tokens were extracted from `/events` and applied to `/library`, `/people`, `/timeline`, and `/search` primary list surfaces
- the same workbench rules were extended to `/review`, `/operations`, and `/graph`: compact task headers, stamp-based metrics, smaller tool actions, and reduced decorative English on operator pages
