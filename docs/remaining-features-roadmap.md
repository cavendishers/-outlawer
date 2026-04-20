# Remaining Features Roadmap

## Goal

This document tracks the product capabilities that are still missing, partially implemented, or implemented only at MVP depth.

It is intended to answer one question clearly:

- what is still not done relative to the original product vision

## Current Snapshot

Current status as of `2026-04-20`:

- core MVP flow is implemented
- Docker deployment, migrations, async jobs, and e2e verification are in place
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
| AI-assisted organization and categorization | `PARTIAL` | extraction and normalization exist, but governance workflows are incomplete |
| Person extraction | `PARTIAL` | core extraction works, but alias/merge/governance is still weak |
| Event extraction | `PARTIAL` | core extraction works and first event curation flow exists, but broader graph editing is still incomplete |
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

Still missing:

- broader graph canvas editing

Suggested deliverables:

- graph curation page
- event editor
- entity editor
- relation editor

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

- `PARTIAL`

Why it matters:

- reprocessing exists, but model-version comparison and controlled replay are not complete
- this becomes critical once extraction prompts and model choices evolve

What is missing:

- selective projection replay
- rollback/replace decision workflow

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

Suggested deliverables:

- replay with selected extractor version before auto-applying it
- rollback/replace decision workflow with clearer operator intent capture

Acceptance target:

- user can compare current projection with a new extraction result before applying it

## Medium Priority

### 5. Back-Office Operations Surface

Status:

- `PARTIAL`

Delivered in the first slice:

- operations page for recent jobs, failed retry actions, recent assets, and note extraction-run inspection
- asset detail now exposes derivative summaries and linked note refs for operator inspection
- single-job detail now exposes payload and result data for runtime debugging

What is missing:

- richer job monitoring dashboard
- raw asset management actions
- merge/review queue dashboard
- queue analytics and operator metrics

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

- `PARTIAL`

Problem:

- `alias_json` and `entity_aliases` both exist, but the system has not fully chosen one canonical path yet

### Embedding Storage Consolidation

Status:

- `PARTIAL`

Problem:

- `note_chunks.embedding_vector` still overlaps conceptually with the dedicated `embeddings` table

### Merge Candidate Actions

Status:

- `TODO`

Problem:

- merge candidates can be generated and listed, but not yet operationally resolved

## Recommended Delivery Order

If the goal is product value rather than pure architecture cleanup, the best next order is:

1. entity and event review workflow
2. graph editing and knowledge curation
3. multimodal quality upgrade
4. extraction replay and versioned reprocessing
5. back-office operations surface
6. API schema completion and read-side service cleanup
7. collaboration and permissions

## Recommendation

If we want the next phase to make the product feel materially more complete, the best next target is:

- `Entity And Event Review Workflow`

Reason:

- it directly improves graph quality
- it reduces extraction noise
- it unlocks trustworthy long-term knowledge accumulation
- it pairs naturally with the graph views that already exist
