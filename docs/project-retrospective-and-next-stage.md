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
- operations baseline: jobs, retries, raw assets, derivative summaries, and extraction-run inspection from a dedicated operations page

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
- operations visibility now has a first dashboard, but deeper admin workflows and metrics are still thin
- some route files still compose read models directly instead of using dedicated query services

## Future Capability Groups

### Highest-value product depth

- broader graph canvas editing
- prompt-version comparison before extraction projection replay

### Platform and maintainability

- strongly typed API contracts across public endpoints
- dedicated read-model query services
- deeper operations dashboard for jobs, assets, runs, and retries

### Product expansion

- multi-user collaboration and permissions
- plugin and external importer system
- mobile-first capture and browse experience

## Recommended Next Stage

The next stage should be:

- **Phase 24: Strongly Typed API Contracts**

This is the best next step because the product surface is now broad enough that implicit dictionaries are becoming the main source of ambiguity:

- multiple endpoints still accept generic payload dictionaries
- frontend pages increasingly depend on stable nullable and optional field behavior
- stronger schemas will reduce regressions before later read-model and admin work expands further

## Phase 24 Scope

- replace generic request dictionaries on core public endpoints with explicit Pydantic schemas
- normalize response models for key read endpoints
- document the contract changes in API docs without schema migrations
- keep the current frontend working while tightening shape guarantees

## Priority-ordered Next Work

1. tighten API contracts with explicit Pydantic schemas
2. continue read-model query service extraction
3. expand graph editing into a canvas-oriented workflow
4. plan multi-user and permissions model
