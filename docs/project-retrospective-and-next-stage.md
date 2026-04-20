# Project Retrospective And Next Stage

Last updated: `2026-04-20`

## Current Capability Summary

The project is now a working single-user MVP for an online AI-assisted knowledge base with the following implemented layers:

- infrastructure baseline: Docker Compose deployment, PostgreSQL, pgvector, RabbitMQ, Redis, MinIO, FastAPI, Next.js, Alembic
- authentication baseline: username/password login with bearer-token auth
- ingestion baseline: text, image, audio, and video upload with raw material preservation
- multimodal derivative baseline: local OCR and ASR fallback, optional OpenRouter enhancement, source attribution, video scene evidence typing
- knowledge graph baseline: notes, entities, events, relations, timeline items, embeddings, style views, extraction evidence
- browse baseline: library, people, events, timeline, search, note detail, story views
- governance baseline: merge review, alias governance, event curation, entity curation, relation edit-in-place
- replay baseline: extraction run history, run diffs, historical run re-apply, replay audit history, operator note on manual replay, and draft approval/rejection before reprocess replaces the active projection

## What Went Well

- data-layer separation stayed intact: raw assets, derivatives, canonical projections, and stylized views were not collapsed together
- deployment and migration discipline was established early, which reduced later rework
- every major feature slice was verified with service tests, builds, and full API e2e
- graph quality work started early enough to avoid an extraction-only dead end
- replay and audit capabilities were added incrementally instead of waiting for a big-bang redesign
- docs, roadmap, and phase tracking stayed synchronized with implementation

## What Went Poorly

- replay safety came later than it should have, so early reprocess behavior was too eager to overwrite current projections
- multimodal semantic quality is still uneven, especially outside video OCR and transcript evidence
- some APIs still rely on generic dictionaries rather than explicit request and response schemas
- graph editing is functional but still feels like back-office form editing more than a real graph workspace
- operations visibility is still developer-centric; there is no true runtime dashboard
- some route files still compose read models directly instead of using dedicated query services

## Future Capability Groups

### Highest-value product depth

- stronger image semantic extraction beyond OCR-only parsing
- stronger audio speaker and context extraction
- broader graph canvas editing

### Platform and maintainability

- strongly typed API contracts across public endpoints
- dedicated read-model query services
- operations dashboard for jobs, assets, runs, and retries

### Product expansion

- multi-user collaboration and permissions
- plugin and external importer system
- mobile-first capture and browse experience

## Recommended Next Stage

The next stage should be:

- **Phase 21: Image Semantic Enrichment**

This is the best next step because replay governance is now in place, and the biggest remaining quality gap is multimodal understanding depth:

- image uploads still lean too heavily on OCR text
- non-text visual clues like scene type, objects, and inferred activities should improve downstream event/entity extraction
- richer visual evidence should flow into later search, timeline, and graph quality work

## Phase 21 Scope

- enrich image derivatives with semantic observations beyond OCR-only text
- preserve structured evidence fragments for visible people, scene hints, objects, and activities
- merge image semantic hints with OCR output into canonical multimodal text
- extend service tests and full API e2e to cover enriched image derivatives

## Priority-ordered Next Work

1. improve image semantic extraction beyond OCR-only text
2. improve audio speaker and context extraction
3. build first operations dashboard for jobs and extraction runs
4. tighten API contracts with explicit Pydantic schemas
5. continue read-model query service extraction
6. expand graph editing into a canvas-oriented workflow
7. plan multi-user and permissions model
