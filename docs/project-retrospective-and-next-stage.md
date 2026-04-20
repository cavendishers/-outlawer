# Project Retrospective And Next Stage

Last updated: `2026-04-20`

## Current Capability Summary

The project is now a working single-user MVP for an online AI-assisted knowledge base with the following implemented layers:

- infrastructure baseline: Docker Compose deployment, PostgreSQL, pgvector, RabbitMQ, Redis, MinIO, FastAPI, Next.js, Alembic
- authentication baseline: username/password login with bearer-token auth
- ingestion baseline: text, image, audio, and video upload with raw material preservation
- multimodal derivative baseline: local OCR and ASR fallback, image semantic hints, optional OpenRouter enhancement, source attribution, video scene evidence typing
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
- multimodal semantic quality is still uneven, especially around audio speaker/context extraction
- some APIs still rely on generic dictionaries rather than explicit request and response schemas
- graph editing is functional but still feels like back-office form editing more than a real graph workspace
- operations visibility is still developer-centric; there is no true runtime dashboard
- some route files still compose read models directly instead of using dedicated query services

## Future Capability Groups

### Highest-value product depth

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

- **Phase 22: Audio Speaker And Context Enrichment**

This is the best next step because replay governance and image semantic hints are now in place, and the biggest remaining multimodal quality gap is audio understanding:

- audio uploads still produce a flat transcript without speaker or context structure
- meeting-style recordings need speaker turns, likely roles, and conversation context to improve entity/event extraction
- richer audio evidence should flow into later search, timeline, and graph quality work

## Phase 22 Scope

- enrich audio derivatives with speaker-turn-like segments when available
- preserve structured context hints for likely conversation type, topics, decisions, and follow-ups
- merge audio context hints with transcript text into canonical multimodal text
- extend service tests and full API e2e to cover enriched audio derivatives

## Priority-ordered Next Work

1. improve audio speaker and context extraction
2. build first operations dashboard for jobs and extraction runs
3. tighten API contracts with explicit Pydantic schemas
4. continue read-model query service extraction
5. expand graph editing into a canvas-oriented workflow
6. plan multi-user and permissions model
