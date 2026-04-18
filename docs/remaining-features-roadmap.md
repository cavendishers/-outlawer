# Remaining Features Roadmap

## Goal

This document tracks the product capabilities that are still missing, partially implemented, or implemented only at MVP depth.

It is intended to answer one question clearly:

- what is still not done relative to the original product vision

## Current Snapshot

Current status as of `2026-04-19`:

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
| Image ingestion | `DONE` | raw storage plus OCR/derivative text available |
| Audio ingestion | `DONE` | raw storage plus ASR/derivative text available |
| Video ingestion | `PARTIAL` | basic derivative extraction exists, but semantic quality is still MVP-grade |
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

Still missing:

- relation edit-in-place beyond create/delete
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

- richer video scene segmentation
- stronger image semantic understanding
- better audio speaker/context extraction
- stronger OpenRouter multimodal prompt and result normalization

Suggested deliverables:

- video frame batching strategy
- multimodal extraction prompt versioning
- richer derivative payload schema
- confidence and source attribution for multimodal outputs

Acceptance target:

- video upload can produce reliable participants, events, time clues, and scene summaries for typical meeting-style input

### 4. Extraction Replay And Versioned Reprocessing

Status:

- `PARTIAL`

Why it matters:

- reprocessing exists, but model-version comparison and controlled replay are not complete
- this becomes critical once extraction prompts and model choices evolve

What is missing:

- extractor version comparison
- side-by-side extraction diff
- selective projection replay
- rollback/replace decision workflow

Suggested deliverables:

- extraction run diff API
- extraction comparison UI
- replay with selected extractor version

Acceptance target:

- user can compare current projection with a new extraction result before applying it

## Medium Priority

### 5. Back-Office Operations Surface

Status:

- `TODO`

What is missing:

- job monitoring dashboard
- failed task retry center
- raw asset management page
- extraction run inspection page
- merge/review queue dashboard

Why it matters:

- current system can run, but operations still depend on developer-level visibility

### 6. Strongly Typed API Contracts

Status:

- `PARTIAL`

What is missing:

- explicit Pydantic request/response schemas for all public APIs
- consistent typed contracts between frontend and backend

Why it matters:

- current system works, but long-term API evolution is riskier without fully explicit schemas

### 7. Query Service Layer For Read Models

Status:

- `PARTIAL`

What is missing:

- dedicated query services for entity/event/timeline reads
- thinner route files across all list/detail endpoints

Why it matters:

- current architecture is improving, but read-side composition is not fully separated yet

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
