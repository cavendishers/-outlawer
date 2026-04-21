# Remaining Features Roadmap

## Goal

This document tracks the product capabilities that are still missing, partially implemented, or implemented only at MVP depth.

It is intended to answer one question clearly:

- what is still not done relative to the original product vision

## Current Snapshot

Current status as of `2026-04-21`:

- core MVP flow is implemented
- Docker deployment, migrations, async jobs, and e2e verification are in place
- Architecture V2 domain packaging has started, but is still mid-migration
- the remaining work is mostly in product depth, graph operations, AI quality, and back-office tooling

## Status Legend

- `DONE`: implemented and verified as part of the current product baseline
- `PARTIAL`: implemented at MVP depth, but not complete enough for long-term product use
- `TODO`: not implemented yet

## Original Vision Mapping

| Capability | Status | Notes |
| --- | --- | --- |
| Username/password login | `DONE` | basic bearer-token auth is available |
| Text ingestion | `DONE` | upload, note creation, extraction flow available |
| Image ingestion | `DONE` | raw storage plus OCR, semantic hints, and derivative text available |
| Audio ingestion | `DONE` | raw storage plus ASR, context hints, transcript segments, and derivative text available |
| Video ingestion | `PARTIAL` | raw storage, sampled OCR/ASR derivatives, scene time ranges, and evidence labels exist; deeper semantic quality is still MVP-grade |
| Raw asset preservation | `DONE` | MinIO-backed storage and raw reads available |
| AI-assisted organization and categorization | `PARTIAL` | extraction, normalization, review, and curation exist, but extraction quality and operator depth still need iteration |
| Person extraction | `PARTIAL` | core extraction plus alias/merge governance exist, but extraction precision and disambiguation still need improvement |
| Event extraction | `PARTIAL` | core extraction and governance flows exist, but broader graph editing and higher-confidence event understanding are still incomplete |
| Similarity and association | `DONE` | similarity search, merge candidates, and review flows are available |
| Person index | `DONE` | people page and entity detail flow available |
| Timeline | `DONE` | timeline page and timeline projections available |
| Event-driven browsing | `DONE` | event detail and related events are available |
| Chunibyo-style display | `DONE` | note and entity story views available |
| Search across keywords/entity/event/similarity | `DONE` | unified search page is live |
| Graph-like browsing experience | `PARTIAL` | multiple graph views exist, but editing and governance are missing |

## High Priority

These are the most important unfinished product capabilities.

### 1. Entity And Event Review Workflow

Status:

- `DONE`

Why it matters:

- extraction quality will plateau quickly without human review tools
- duplicate people and duplicate events will accumulate over time
- this is the missing operational layer between AI extraction and reliable knowledge graph quality

Delivered:

- merge candidate review API
- accept/reject merge operations
- entity merge and event merge flows
- manual alias confirmation
- audit trail for review actions
- review queue and context pages

Verification:

- review workflow is covered by `server/scripts/e2e_review_flow.py`
- dependent graph references are rewritten during accepted merges

### 2. Graph Editing And Knowledge Curation

Status:

- `PARTIAL`

Why it matters:

- the current graph is mostly generated and displayed
- without manual editing, the graph cannot become a reliable long-term knowledge base

Delivered in the first slice:

- event curation API
- event field correction for title, summary, description, time, location, and status
- participant add/remove for events
- relation add/remove for event-centered graph maintenance
- web event curation page
- dedicated curation e2e

Delivered in the second slice:

- entity curation API
- entity field correction for canonical name, display name, description, type, status, and seen timestamps
- trusted alias add/remove flow for entity governance
- web entity curation page
- dedicated entity curation e2e

Delivered in the third slice:

- relation edit-in-place for curated graph links
- entity-centered relation add/update/remove workflow
- event curation relation updates without delete-and-recreate in the UI flow
- dedicated e2e coverage for mixed entity/event relation editing

Delivered in the fourth slice:

- event detail page now includes an association workspace for stepping through related events, shared participants, and review shortcuts
- entity story page now includes a timeline workspace for stepping through people-related fragments and side-axis event echoes
- graph-first navigation improved without changing existing review and curation governance flows

Delivered in the fifth slice:

- shared `/graph` workspace route now unifies event, entity, and overview graph entry points
- node selection is URL-driven so the current focus can be revisited or shared
- a dedicated node-detail API now returns connected nodes, connected edges, time context, and anchor actions for the current focus node
- the graph inspector can now keep users inside one workspace while traversing adjacent nodes and timeline anchors

Delivered in the sixth slice:

- the shared graph workspace now supports inline add/remove for event participants using the active graph neighborhood
- event and entity nodes can now add, update, and remove graph relations directly inside the node inspector
- graph mutations now refresh the shared workspace locally after each successful inline edit instead of forcing a navigation back to standalone curation pages

Delivered in the seventh slice:

- the shared graph workspace now includes `all / events / people / timeline` viewing modes
- timeline backbone segments are now selectable inside the shared graph shell and can focus event nodes without route thrash
- people-timeline and event-network navigation now coexist in one workspace instead of being split between separate page-local affordances
- the shared graph workspace now has skeleton loading panels, empty-state fallback, active-node emphasis, and clearer inline validation / busy feedback for daily use

Delivered in the eighth slice:

- visible graph edges can now be focused directly inside the shared workspace instead of only being implied by node cards
- graph workspace now exposes an edge spotlight rail with quick pivot actions to either endpoint
- broader graph exploration has started moving from node-only inspection toward graph-native relation inspection

Still missing:

- broader graph canvas editing
- deeper operations dashboards beyond the current backlog and routing signals

Suggested deliverables:

- broader graph canvas editing
- saved viewpoints or stronger graph-neighborhood editing primitives
- richer operator analytics around queue latency, asset actions, and admin workflows

Acceptance target:

- user can correct an extracted event or relation without touching raw data

### 3. Multimodal Quality Upgrade

Status:

- `PARTIAL`

Why it matters:

- current multimodal flow is functional, but still closer to fallback parsing than high-quality semantic understanding
- video understanding is the weakest part of the stack right now

What is missing:

- prompt versioning and result comparison before projection replay

Delivered in the first upgrade slice:

- local OCR/ASR derivatives now keep source attribution snippets
- local multimodal parsing can be merged with OpenRouter enhancement instead of short-circuiting after the first local success
- canonical multimodal text now includes richer observed people, events, locations, confidence, and source fragments
- service-level regression tests cover multimodal payload merging

Delivered in the second upgrade slice:

- local video parsing samples frames according to media duration
- video frame OCR evidence now includes scene labels and time ranges
- multimodal derivative payloads now preserve `video_scene_segments`
- canonical multimodal text labels direct evidence, model inference, and mixed evidence separately
- OpenRouter multimodal prompts request the same evidence attribution structure
- service-level regression tests cover scene segments and evidence typing

Delivered in the third upgrade slice:

- image derivatives now include structured scene, object, action, layout, and document-type hints beyond OCR-only text
- images with little or no OCR text can still produce local semantic fallback text from title, image metadata, and visual-layout hints
- OpenRouter multimodal prompts now request the same image semantic fields for model-enhanced parsing
- full API e2e verifies image upload through derived `analysis_json` and `normalized_text`

Delivered in the fourth upgrade slice:

- audio derivatives now include conversation type, speaker hints, topic hints, decision hints, follow-up hints, and time-ordered transcript segments when available
- audio files with little or no transcript can still produce conservative context fallback text from title-level signals
- OpenRouter multimodal prompts now request the same audio context and segment fields for model-enhanced parsing
- full API e2e verifies audio upload through derived `analysis_json` and `normalized_text`

Suggested deliverables:

- multimodal extraction prompt versioning
- richer derivative payload schema

Acceptance target:

- video upload can produce reliable participants, events, time clues, and scene summaries for typical meeting-style input

### 4. Extraction Replay And Versioned Reprocessing

Status:

- `DONE`

Why it matters:

- reprocessing exists, but model-version comparison and controlled replay are not complete
- this becomes critical once extraction prompts and model choices evolve

Delivered in the first replay slice:

- note APIs now expose extraction run history and single-run summaries
- note APIs now expose side-by-side diff snapshots between any two runs of the same note
- note detail UI now shows recent extraction runs and the latest diff snapshot
- full API e2e now verifies extraction run list/detail/compare endpoints

Delivered in the second replay slice:

- note APIs now support applying a selected historical extraction run back into the current projection
- extraction run status now distinguishes `applied` and `superseded` runs for note-scoped replay history
- note detail UI now marks the currently applied run and supports rolling back to another saved run
- full API e2e now verifies reprocess plus historical run re-apply flow

Delivered in the third replay slice:

- note APIs now expose replay action history for automatic and manual projection applies
- manual replay apply requests can carry an operator note for audit context
- note detail UI now shows replay action history alongside run history and diff context
- full API e2e now verifies replay action audit persistence after a manual rollback/apply

Delivered in the fourth replay slice:

- note reprocess now creates a `ready_for_review` extraction draft when an applied run already exists
- explicit approve and reject endpoints are available for reviewable draft runs
- active projection stays unchanged until draft approval
- note detail UI now separates draft candidates, rejected runs, current projection, and historical rollback runs
- full API e2e now verifies draft creation, approval, rejection, and active-projection preservation

Delivered in the fifth replay slice:

- `extraction_runs` now carry provider, model, prompt, schema, input-hash, and parent lineage metadata
- immutable `projection_versions` now record each projection apply event
- notes now keep an explicit `active_projection_id` pointer
- replay audit payloads now include projection-version ids and version metadata
- full API e2e now verifies projection-version id persistence through draft approval

## Medium Priority

### 5. Back-Office Operations Surface

Status:

- `PARTIAL`

Delivered in the first slice:

- operations page for recent jobs, failed retry actions, recent assets, and note extraction-run inspection
- asset detail now exposes derivative summaries and linked note refs for operator inspection
- single-job detail now exposes payload and result data for runtime debugging

Delivered in the second slice:

- `/api/v1/operations/overview` now returns backlog-oriented operations signals instead of forcing the frontend to stitch them together
- operations console now surfaces failed jobs, reviewable extraction drafts, pending merge candidates, recent operator actions, and asset type distribution in one place
- operators now get direct routing links from backlog signals into note detail, review, and curation pages

What is missing:

- richer job monitoring dashboard
- raw asset management actions
- queue analytics and operator metrics
- broader admin workflows beyond monitoring and routing

Why it matters:

- current system can run, but operations still depend on developer-level visibility

### 6. Strongly Typed API Contracts

Status:

- `DONE`

Delivered:

- note create and replay actions now use explicit Pydantic request schemas
- review accept/reject and alias-confirm actions now use explicit request schemas
- entity/event curation write endpoints now use explicit request schemas
- OpenAPI contract tests now lock these request bodies against regressing back to open-ended payloads

Why it matters:

- contract drift risk is lower now that the broadest write surfaces are schema-driven

### 7. Query Service Layer For Read Models

Status:

- `DONE`

Delivered:

- dedicated query services for note, entity, event, and timeline read endpoints
- thinner route files for the main browse/detail surfaces
- shared participant and related-event read helpers reused by review and curation contexts
- review e2e paging hardened so verification remains stable as candidate volume grows

Why it matters:

- route-level sprawl is lower now that main read models have a stable composition seam

## Lower Priority

### 8. Collaboration And Permissions

Status:

- `TODO`

What is missing:

- multi-user sharing
- role-based permissions
- workspace-level isolation
- shared knowledge bases

Why it matters:

- important for product expansion, but not necessary for single-user MVP

### 9. Plugin And Integration System

Status:

- `TODO`

What is missing:

- external importer hooks
- plugin runtime or extension mechanism
- sync integrations with third-party tools

### 10. Mobile Experience

Status:

- `TODO`

What is missing:

- mobile-first ingestion flow
- mobile-friendly graph browsing
- capture-first UX for quick note/audio/photo upload

## Hidden Technical Debts That Still Affect Product Work

These are not direct user-facing features, but they still block future capabilities.

### Alias Model Consolidation

Status:

- `DONE`

Resolved:

- `entity_aliases` is now the canonical alias store
- `alias_json` is transitional cache/display data only

### Embedding Storage Consolidation

Status:

- `DONE`

Resolved:

- vectors now persist through `embeddings`
- `note_chunks.embedding_vector` has been removed

### Merge Candidate Actions

Status:

- `TODO`

Problem:

- merge candidates can be generated and listed, but not yet operationally resolved

## Recommended Delivery Order

If the goal is product value rather than pure architecture cleanup, the best next order is:

1. graph editing and knowledge curation
2. multimodal quality upgrade
3. back-office operations surface
4. API schema completion and read-side service cleanup
5. collaboration and permissions
6. mobile experience
7. domain packaging and internal modularization

### 7. Domain Packaging And Internal Modularization

Status:

- `PARTIAL`

Why it matters:

- the product has grown beyond MVP size, so backend ownership needs to follow domain boundaries instead of one large horizontal services layer
- extraction, replay, projection, and read-model concerns need cleaner seams before later capabilities become expensive to extend

Delivered in the first slice:

- introduced `server/app/domains/` as the new backend package root for domain-first modules
- created initial `domains/extraction` and `domains/replay` modules
- moved extraction metadata helpers, worker pipeline orchestration, and replay diff logic into those modules
- updated selected API, worker, query-service, and test imports to depend on the new domain seams
- preserved compatibility shims so the migration can continue incrementally without breaking current behavior

Delivered in the second slice:

- moved replay service behavior into `domains/replay/service.py`
- reduced `services/extraction_run_service.py` to a compatibility export so older imports can keep working during the transition
- verified replay-related tests and full API e2e still pass after the implementation move

Delivered in the third slice:

- moved extraction payload orchestration and merge heuristics into `domains/extraction/extractor.py`
- updated the extraction pipeline and extractor tests to depend on the extraction domain package directly
- reduced `services/extractor_service.py` to a compatibility export while the migration continues

Delivered in the fourth slice:

- moved projection persistence and graph materialization into `domains/projection/service.py`
- updated replay and extraction flows to depend on the projection domain package directly
- reduced `services/projection_service.py` to a compatibility export while the migration continues

Delivered in the fifth slice:

- moved note, entity, event, and timeline query composition into `domains/retrieval/*`
- updated API routes and key read-side callers to depend on the retrieval domain package directly
- reduced the old query service modules to compatibility exports while the migration continues

Delivered in the sixth slice:

- moved merge review, alias confirmation, event/entity curation, and governance object-summary helpers into `domains/governance/*`
- updated review, curation, and operations callers to depend on the governance domain package directly
- reduced the old review and curation service modules to compatibility exports while the migration continues
- hardened merge rewrites so duplicate alias and participant rows are resolved before flush during governance-driven merges

Delivered in the seventh slice:

- moved graph overview, related-event suggestion, and entity timeline fragment read models into `domains/retrieval/graph_query.py`
- moved graph workspace composition into `domains/retrieval/graph_workspace.py`
- updated graph API routes, retrieval queries, governance readers, and graph tests to depend on retrieval domain paths directly
- reduced the old graph service modules to compatibility exports while the migration continues

Delivered in the eighth slice:

- moved unified search composition into `domains/retrieval/search_query.py`
- updated search API routes to depend on retrieval-domain search helpers directly
- reduced the old search service module to a compatibility export while the migration continues
- kept OpenAPI and full Docker e2e green after the search read model moved into the retrieval domain

Still missing:

- projection module packaging
- knowledge and operations domain packaging
- further breakup of oversized legacy services

Acceptance target:

- backend modules are organized primarily by domain responsibility rather than a generic `services` bucket

## Recommendation

If we want the next phase to make the product feel materially more complete, the best next target is:

- `Graph Editing And Knowledge Curation`

Reason:

- replay/versioning safety is now in place, so the next product multiplier is stronger graph correction depth
- it directly improves long-term graph quality after extraction
- it gives operators more leverage than another internal-only refactor
- it pairs naturally with the graph views that already exist
