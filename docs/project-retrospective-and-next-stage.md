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
- the new manual-authoring and collection workflows now need real usage feedback before their next depth slice is chosen
- operations visibility now has a first dashboard, but deeper admin workflows and metrics are still thin
- a few lower-priority read endpoints can still be moved onto the same query-service pattern over time

## Future Capability Groups

### Highest-value product depth

- validate manual-authoring and collection workflows with real cases
- collection collaboration and permissions if multiple operators begin sharing worksets
- destination-specific publishing only after a concrete export target is selected

### Platform and maintainability

- deeper operations dashboard for jobs, assets, runs, and retries
- prompt-version comparison before extraction projection replay
- broader freeform canvas editing when real usage demonstrates the need

### Product expansion

- multi-user collaboration and permissions
- plugin and external importer system
- mobile-first capture and browse experience

## Delivered Product-Depth Stage

Phase 31–34 are now complete:

1. manual entity/event creation with explicit contracts, source evidence, and audit actions
2. create-and-connect flow inside `/graph`
3. topic/case collections for notes, raw assets, events, entities, and saved viewpoints
4. curated collection timelines, editable story compilation, and Markdown/JSON export
5. searchable collection intake, cross-surface add actions, evidence readback, member management, coverage signals, and collection-scoped graph views

## Next Selection Rule

Do not start another broad phase automatically. Use real collection and authoring workflows to choose between collaboration/permissions, publishing destinations, AI quality work, operations depth, or optional graph-canvas expansion.

Deferred by current product priority:

- extraction quality benchmarking and semantic embedding replacement
- formal CI/release automation
- deeper operations analytics
- multi-user permissions, plugin integrations, and mobile-first capture
