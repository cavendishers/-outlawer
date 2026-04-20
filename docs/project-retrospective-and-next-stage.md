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
- broad write surfaces now have explicit API contracts, which lowers frontend/backend drift risk
- the new query-service seam now gives browse pages a cleaner place to evolve without bloating route files again

## What Went Poorly

- replay safety came later than it should have, so early reprocess behavior was too eager to overwrite current projections
- multimodal prompt/version governance still needs stronger comparison tooling as prompts evolve
- response models and some lower-priority endpoints still need the same level of explicit contract hardening as the main write surfaces
- graph editing is functional but still feels like back-office form editing more than a real graph workspace
- operations visibility now has a first dashboard, but deeper admin workflows and metrics are still thin
- a few lower-priority read endpoints can still be moved onto the same query-service pattern over time

## Future Capability Groups

### Highest-value product depth

- broader graph canvas editing
- prompt-version comparison before extraction projection replay

### Platform and maintainability

- dedicated read-model query services
- deeper operations dashboard for jobs, assets, runs, and retries

### Product expansion

- multi-user collaboration and permissions
- plugin and external importer system
- mobile-first capture and browse experience

## Recommended Next Stage

The next stage should be:

- **Phase 26: Graph Workspace And Canvas Editing**

This is the best next step because the architecture seams are now cleaner, which means the biggest remaining gap is product depth rather than route structure:

- graph correction is available but still feels like back-office forms
- event-to-event association browsing is stronger than before, but not yet a true workspace
- the new query services give us a better foundation for richer graph UI without tangling route handlers again

## Phase 26 Scope

- expand event-to-event association views and people-timeline fragments into a clearer graph workspace
- add graph-first navigation and editing affordances beyond flat forms
- preserve current curation and review governance while improving the graph mental model

## Priority-ordered Next Work

1. expand graph editing into a canvas-oriented workflow
2. deepen operations dashboards and operator workflows
3. plan multi-user and permissions model
4. design plugin and external importer seams
