# Online Knowledge Base

An online, AI-assisted knowledge base inspired by Obsidian, with multimodal ingestion, structured knowledge extraction, timeline browsing, entity indexing, and stylized story views.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, Celery
- AI Gateway: OpenRouter
- Queue: RabbitMQ
- Database: PostgreSQL, pgvector
- Cache: Redis
- Object Storage: MinIO
- Deployment: Docker Compose
- Migrations: Alembic

## Repository Layout

```text
project/
  web/
  server/
  deploy/
  docs/
```

Detailed design documents live in [`docs/current-system-overview.md`](/Users/hongan/Documents/fxxk/docs/current-system-overview.md), [`docs/architecture.md`](/Users/hongan/Documents/fxxk/docs/architecture.md), [`docs/architecture-review.md`](/Users/hongan/Documents/fxxk/docs/architecture-review.md), [`docs/remaining-features-roadmap.md`](/Users/hongan/Documents/fxxk/docs/remaining-features-roadmap.md), [`docs/phase-11-review-workflow-plan.md`](/Users/hongan/Documents/fxxk/docs/phase-11-review-workflow-plan.md), [`docs/phase-12-event-curation-plan.md`](/Users/hongan/Documents/fxxk/docs/phase-12-event-curation-plan.md), [`docs/api-contract.md`](/Users/hongan/Documents/fxxk/docs/api-contract.md), [`docs/database-design.md`](/Users/hongan/Documents/fxxk/docs/database-design.md), [`docs/ai-extraction-format.md`](/Users/hongan/Documents/fxxk/docs/ai-extraction-format.md), [`docs/deployment.md`](/Users/hongan/Documents/fxxk/docs/deployment.md), [`docs/migration-guide.md`](/Users/hongan/Documents/fxxk/docs/migration-guide.md), [`docs/mvp-plan.md`](/Users/hongan/Documents/fxxk/docs/mvp-plan.md), [`docs/development-phases.md`](/Users/hongan/Documents/fxxk/docs/development-phases.md), and [`docs/documentation-workflow.md`](/Users/hongan/Documents/fxxk/docs/documentation-workflow.md).
Operational runbooks live in [`docs/operations.md`](/Users/hongan/Documents/fxxk/docs/operations.md).

## Product Summary

The system accepts text, audio, image, and video inputs. Raw materials are preserved separately. AI processing runs asynchronously to extract entities, events, timelines, relations, embeddings, and stylized story views without overwriting the source material.

For multimodal assets, the worker now uses a layered parser strategy:

- image: local Tesseract OCR first, then optional OpenRouter enrichment
- audio: local Vosk speech transcription
- video: frame OCR plus audio transcription, then normalized text extraction

## Current Delivery Status

- Phase `0` through Phase `13` are implemented and verified in Docker.
- Architecture hardening completed for core API contracts, pagination metadata, shared serialization, job dispatch boundaries, and pipeline service separation.
- Auth is bearer-token based.
- Uploads are API-proxied into MinIO, and raw reads return original text or a presigned `raw_url`.
- Reprocessing preserves extraction history through `extraction_runs` and rewrites canonical projections conservatively.
- Unified search is available in the web app for note keywords, entity hits, event hits, and note-to-note similarity recall.
- Review workflow is available in the web app for merge-candidate filtering, accept/reject decisions, alias confirmation, and audited entity/event merges.
- Event curation is available in the web app for manual correction of event fields, participants, and event-centered graph relations.
- Entity curation is available in the web app for manual correction of canonical/display names, type, status, seen timestamps, and trusted aliases.

## Quick Start

```bash
docker compose -f deploy/compose/docker-compose.dev.yml up --build -d
python3 server/scripts/e2e_api_flow.py --phase full
```

Default local entrypoints:

- Web UI: `http://localhost:3000`
- API: `http://localhost:8000/api/v1`
- Nginx: `http://localhost:8088`

Local Docker development reads the repository root `.env` automatically. A matching `server/.env` is also available for direct backend runs outside Docker. Both are gitignored and should stay local-only.

To enable AI extraction through OpenRouter, set these environment variables in `.env` before starting Docker:

```bash
EXTRACTOR_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=qwen/qwen3-next-80b-a3b-instruct:free
```

`OPENROUTER_MODEL` is optional. If it is omitted, the backend sends a free-model fallback list through OpenRouter's `models` routing parameter. Override the full list with `OPENROUTER_MODELS` when needed.

OpenRouter accepts at most three models per `models` fallback request, so the backend automatically sends the configured free-model list in batches of three. If one batch is rate-limited, the next batch is tried before falling back to the local heuristic extractor.

Text notes now use this pipeline by default in local development when `EXTRACTOR_PROVIDER=openrouter` is set:

- preserve original note/raw asset data
- call OpenRouter for structured extraction
- persist entities, events, relations, timeline items, extraction evidence, and merge candidates
- generate a separate chunibyo-style story payload without overwriting canonical knowledge

When OpenRouter free-model quota is exhausted, the backend falls back to local multimodal parsing for image, audio, and video ingestion so the note pipeline can still continue with normalized derivative text.

## Development Rules

- Keep `web/`, `server/`, and `deploy/` responsibilities separate.
- Treat raw assets, canonical text, structured knowledge, and stylized views as different data layers.
- All schema changes must go through Alembic migration files.
- Never rely on ORM auto-create for production schema management.
- Prefer small, reversible changes with clear migration history.
- New API endpoints should be versioned under `/api/v1`.
- Long-running AI and media processing must be asynchronous.
- MinIO stores original files; PostgreSQL stores structured data; pgvector stores embeddings.
- Docker Compose is the default local and initial production deployment path.
- Every completed phase must be manually reflected in the related docs.
- `api` and `worker` images include `ffmpeg` and `tesseract`; backend Python dependencies include `vosk` for local ASR fallback.

## Verification Baseline

Verified on `2026-04-19`:

- `python3 -m compileall server/app server/tests server/scripts`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api alembic upgrade head`
- `npm run build` in `web/`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_review_flow.py`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_curation_flow.py`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_entity_curation_flow.py`

## Database Migration Rules

- Every schema change requires a committed Alembic migration file.
- Do not merge model changes without the matching migration.
- Review generated migrations manually before applying them.
- Production rollout order is: migration job first, then API and worker services.

## API Conventions

- Use REST endpoints under `/api/v1`.
- Standard response shape:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

- List endpoints should support `page` and `page_size`, and return `items`, `total`, `page`, `page_size`, and `total_pages`.
- Upload and AI processing are separate steps.
- Async processing endpoints should return a `job_id`.

## Docker Conventions

- Keep service Dockerfiles in `deploy/docker/`.
- Keep compose files in `deploy/compose/`.
- Use environment-variable driven configuration only.
- Mount persistent volumes for PostgreSQL, RabbitMQ, Redis, and MinIO data.
- Run migrations as an explicit deployment step.

## Suggested Startup Order

1. PostgreSQL
2. RabbitMQ
3. Redis
4. MinIO
5. Migration job
6. API
7. Worker
8. Web
9. Nginx

## Initial Milestones

1. Set up `server/` with FastAPI, SQLAlchemy, Alembic, and auth.
2. Set up MinIO-backed raw asset ingestion.
3. Add `notes` and `ai_jobs` flow.
4. Add Celery and RabbitMQ workers.
5. Add entity, event, timeline, and relation extraction.
6. Build the first Next.js pages.
7. Add stylized story views.

## Documentation Tracking

- Use [`docs/development-phases.md`](/Users/hongan/Documents/fxxk/docs/development-phases.md) as the delivery checklist.
- Use [`docs/documentation-workflow.md`](/Users/hongan/Documents/fxxk/docs/documentation-workflow.md) for the manual documentation update rule.
- When a phase is completed, manually update the phase status and the related documents listed in that phase.
