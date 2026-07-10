# Project Retrospective And Next Stage

Last updated: `2026-07-11`

## Current Capability Summary

The project is now a working single-user MVP for an online AI-assisted knowledge base with the following implemented layers:

- infrastructure baseline: Docker Compose deployment, PostgreSQL, pgvector, RabbitMQ, Redis, MinIO, FastAPI, Next.js, Alembic
- authentication baseline: username/password login with bearer-token auth
- ingestion baseline: text, image, audio, and video upload with raw material preservation
- multimodal derivative baseline: local OCR and ASR fallback, image semantic hints, audio context hints, optional OpenRouter enhancement, source attribution, video scene evidence typing
- knowledge graph baseline: notes, entities, events, relations, timeline items, embeddings, style views, extraction evidence
- browse baseline: library, people, events, timeline, search, note detail, story views
- governance baseline: merge review, alias governance, event/entity/relation curation, saved graph viewpoints, non-destructive conflict dispositions, and explained path discovery
- replay baseline: extraction run history, run diffs, historical run re-apply, replay audit history, operator note on manual replay, and draft approval/rejection before reprocess replaces the active projection
- operations baseline: jobs, retries, raw assets, derivative summaries, extraction-run inspection, graph quality counters, and graph-governance audit activity

## What Went Well

- data-layer separation stayed intact: raw assets, derivatives, canonical projections, and stylized views were not collapsed together
- deployment and migration discipline was established early, which reduced later rework
- every major feature slice was verified with service tests, builds, and full API e2e
- graph quality work started early enough to avoid an extraction-only dead end
- replay and audit capabilities were added incrementally instead of waiting for a big-bang redesign
- docs, roadmap, and phase tracking stayed synchronized with implementation
- broad write surfaces now have explicit API contracts, which lowers frontend/backend drift risk
- the new query-service seam now gives browse pages a cleaner place to evolve without bloating route files again

## What Went Poorly

- replay safety came later than it should have, so early reprocess behavior was too eager to overwrite current projections
- multimodal prompt/version governance still needs stronger comparison tooling as prompts evolve
- a smaller tail of lower-priority or admin-oriented endpoints still needs the same level of explicit contract hardening as the main public APIs
- canonical knowledge still depends too heavily on extraction because missing entities and events cannot yet be authored directly with evidence
- operations visibility now has a first dashboard, but deeper admin workflows and metrics are still thin
- a few lower-priority read endpoints can still be moved onto the same query-service pattern over time

## Future Capability Groups

### Highest-value product depth

- manual entity/event creation with evidence and audit history
- graph-context create-and-connect workflows
- topic/case collections and curated timeline/story compilation

### Platform and maintainability

- deeper operations dashboard for jobs, assets, runs, and retries
- prompt-version comparison before extraction projection replay
- broader freeform canvas editing when real usage demonstrates the need

### Product expansion

- multi-user collaboration and permissions
- plugin and external importer system
- mobile-first capture and browse experience

## Recommended Next Stage

The next stage should be:

- **Phase 31: Manual Knowledge Authoring Loop**

This is the best next step after analysis traceability and graph governance because the remaining daily-use gap is no longer inspection or correction:

- users can inspect, correct, retain, postpone, and explain extracted knowledge, but cannot yet create every missing canonical event/person directly
- graph path discovery can reveal a missing link, so the next natural action is to create the missing node or evidence without leaving the workspace
- manual objects must preserve provenance and audit rules instead of bypassing the raw/derived/canonical boundaries

## Phase 31 Scope

- add explicit manual-create contracts for entities and events
- add graph-context creation that can connect the new object to the active node in one flow
- attach source-note/raw-asset evidence to manually created or existing knowledge records
- log manual creation, relation creation, and evidence attachment in the governance audit stream
- keep manually authored knowledge independently queryable from stylized story views

## Priority-ordered Next Work

1. manual entity/event creation with explicit contracts and audit actions
2. create-and-connect flow inside `/graph`
3. manual evidence attachment to existing notes/assets
4. topic/case collections that group notes, assets, events, entities, and saved viewpoints
5. curated timeline/story compilation and export from a collection

Deferred by current product priority:

- extraction quality benchmarking and semantic embedding replacement
- formal CI/release automation
- deeper operations analytics
- multi-user permissions, plugin integrations, and mobile-first capture
