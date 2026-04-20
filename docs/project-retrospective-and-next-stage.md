# Project Retrospective And Next Stage

Last updated: `2026-04-20`

## Current Capability Summary

The project is now a working single-user MVP for an online AI-assisted knowledge base with the following implemented layers:

- infrastructure baseline: Docker Compose deployment, PostgreSQL, pgvector, RabbitMQ, Redis, MinIO, FastAPI, Next.js, Alembic
- authentication baseline: username/password login with bearer-token auth
- ingestion baseline: text, image, audio, and video upload with raw material preservation
- multimodal derivative baseline: local OCR and ASR fallback, image semantic hints, audio context hints, optional OpenRouter enhancement, source attribution, video scene evidence typing
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
- multimodal prompt/version governance still needs stronger comparison tooling as prompts evolve
- some APIs still rely on generic dictionaries rather than explicit request and response schemas
- graph editing is functional but still feels like back-office form editing more than a real graph workspace
- operations visibility is still developer-centric; there is no true runtime dashboard
- some route files still compose read models directly instead of using dedicated query services

## Future Capability Groups

### Highest-value product depth

- broader graph canvas editing
- prompt-version comparison before extraction projection replay

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

- **Phase 23: Operations Dashboard Foundation**

This is the best next step because the system can now ingest, extract, replay, review, and curate, but runtime visibility is still developer-centric:

- failed jobs and retries require API or database knowledge
- raw assets and derivative payloads are hard to inspect from the product surface
- extraction runs and replay state need an operator-friendly inspection entry point

## Phase 23 Scope

- build an operations page for jobs, failed retries, recent assets, and extraction runs
- add backend read endpoints or reuse existing endpoints where possible without schema changes
- expose derivative inspection summaries for raw assets
- keep the page admin-only under the current simple auth model

## Priority-ordered Next Work

1. build first operations dashboard for jobs and extraction runs
2. tighten API contracts with explicit Pydantic schemas
3. continue read-model query service extraction
4. expand graph editing into a canvas-oriented workflow
5. plan multi-user and permissions model
