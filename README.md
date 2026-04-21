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

Detailed design documents live in [`docs/current-system-overview.md`](/Users/hongan/Documents/fxxk/docs/current-system-overview.md), [`docs/architecture.md`](/Users/hongan/Documents/fxxk/docs/architecture.md), [`docs/architecture-review.md`](/Users/hongan/Documents/fxxk/docs/architecture-review.md), [`docs/architecture-v2-blueprint.md`](/Users/hongan/Documents/fxxk/docs/architecture-v2-blueprint.md), [`docs/remaining-features-roadmap.md`](/Users/hongan/Documents/fxxk/docs/remaining-features-roadmap.md), [`docs/project-retrospective-and-next-stage.md`](/Users/hongan/Documents/fxxk/docs/project-retrospective-and-next-stage.md), [`docs/phase-11-review-workflow-plan.md`](/Users/hongan/Documents/fxxk/docs/phase-11-review-workflow-plan.md), [`docs/phase-12-event-curation-plan.md`](/Users/hongan/Documents/fxxk/docs/phase-12-event-curation-plan.md), [`docs/phase-26-graph-workspace-plan.md`](/Users/hongan/Documents/fxxk/docs/phase-26-graph-workspace-plan.md), [`docs/api-contract.md`](/Users/hongan/Documents/fxxk/docs/api-contract.md), [`docs/database-design.md`](/Users/hongan/Documents/fxxk/docs/database-design.md), [`docs/ai-extraction-format.md`](/Users/hongan/Documents/fxxk/docs/ai-extraction-format.md), [`docs/deployment.md`](/Users/hongan/Documents/fxxk/docs/deployment.md), [`docs/migration-guide.md`](/Users/hongan/Documents/fxxk/docs/migration-guide.md), [`docs/mvp-plan.md`](/Users/hongan/Documents/fxxk/docs/mvp-plan.md), [`docs/development-phases.md`](/Users/hongan/Documents/fxxk/docs/development-phases.md), and [`docs/documentation-workflow.md`](/Users/hongan/Documents/fxxk/docs/documentation-workflow.md).
Operational runbooks live in [`docs/operations.md`](/Users/hongan/Documents/fxxk/docs/operations.md).

## Product Summary

The system accepts text, audio, image, and video inputs. Raw materials are preserved separately. AI processing runs asynchronously to extract entities, events, timelines, relations, embeddings, and stylized story views without overwriting the source material.

For multimodal assets, the worker now uses a layered parser strategy:

- image: local Tesseract OCR first, then optional OpenRouter enrichment
- image derivatives also include structured semantic hints for likely scene, visible objects, visible actions, image layout, and document/photo type
- audio: local Vosk speech transcription, then optional OpenRouter enrichment
- audio derivatives also include conversation type, speaker hints, topic hints, decision hints, follow-up hints, and time-ordered transcript segments when available
- video: sampled frame OCR plus audio transcription, then optional OpenRouter enrichment
- multimodal derivatives now preserve source attribution snippets so later extraction can see what came from OCR frames versus audio transcript
- video derivatives also preserve sampled scene time ranges and label direct OCR/ASR evidence separately from model-inferred context

## Current Delivery Status

- Phase `0` through Phase `25` are implemented and verified in Docker.
- Architecture V2 blueprint `Phase A: Source-of-truth cleanup` is now implemented and verified in Docker.
- Architecture V2 blueprint `Phase B: Extraction/projection versioning` is now implemented and verified in Docker.
- Architecture V2 blueprint `Phase C: Domain packaging` is now in progress; the first three slices introduced `app.domains.extraction` and `app.domains.replay`, moved extraction metadata, extraction payload orchestration, worker pipeline, replay diff logic, and replay service behavior behind those seams, and kept compatibility shims for legacy imports.
- Architecture hardening completed for core API contracts, pagination metadata, shared serialization, job dispatch boundaries, and pipeline service separation.
- Auth is bearer-token based.
- Uploads are API-proxied into MinIO, and raw reads return original text or a presigned `raw_url`.
- Reprocessing preserves extraction history through `extraction_runs` and rewrites canonical projections conservatively.
- Note detail now surfaces extraction run history and a latest diff snapshot to support safer reprocessing review.
- Note detail can now re-apply a saved extraction run so the current projection can be rolled back to an earlier version.
- Replay actions are now auditable from the note detail page, including optional operator notes on manual apply.
- Reprocessing now creates a reviewable extraction draft when a note already has an active projection, and the active projection stays unchanged until explicit approve or reject.
- Unified search is available in the web app for note keywords, entity hits, event hits, and note-to-note similarity recall.
- Review workflow is available in the web app for merge-candidate filtering, accept/reject decisions, alias confirmation, and audited entity/event merges.
- Event curation is available in the web app for manual correction of event fields, participants, and event-centered graph relations, including relation edit-in-place.
- Entity curation is available in the web app for manual correction of canonical/display names, type, status, seen timestamps, trusted aliases, and entity-centered graph relations.
- Image ingestion now preserves semantic derivative fields beyond OCR-only text, including scene, object, action, layout, and document-type hints.
- Audio ingestion now preserves context derivative fields beyond flat transcripts, including speaker hints, topics, decisions, follow-ups, and transcript segments.
- 运维后台基础页已经上线，可检查 jobs、失败重试、原始 assets、派生摘要和 note extraction runs，并通过 `/api/v1/operations/overview` 汇总失败任务、待审抽取、待合并候选和最近操作动作。
- note 创建/回放、review 审核、entity/event curation 写接口现在都使用显式 Pydantic 请求模型，并通过 OpenAPI 契约测试锁定字段边界。
- auth、assets、jobs、notes、entities、events、timeline、story views 的核心响应模型也已经显式化，OpenAPI 可直接反映分页、详情、回放 diff 和图谱概览结构。
- search、review、curation 的聚合响应也已经显式化，OpenAPI 现在能直接展示统一检索、merge candidate、review context、curation context 与关系编辑结果结构。
- note、entity、event、timeline 的主要读接口现在都通过独立 query service 组装，路由层只保留参数与响应封装。
- alias 读写现在统一走 `entity_aliases`，`entities.alias_json` 仅保留为过渡期缓存/展示字段。
- note、entity、event 的向量现在统一落在 `embeddings`，`note_chunks.embedding_vector` 已移除。
- 事件参与者事实现在以 `event_entities` 为唯一真相源，不再镜像写入 `relations(participates_in)`。
- `extraction_runs` 现在会记录 provider/model/prompt/schema/input hash/lineage/projection status 等版本元数据。
- `projection_versions` 和 `notes.active_projection_id` 已上线，回放、审批、自动应用都会显式写入投影版本记录。
- 事件详情页和人物故事页现在都带有第一版图谱工作台，可直接沿关联事件和时间片段继续跳转。
- `/graph` 共享图谱工作台和 `/api/v1/graph/workspace` 读接口已经上线，支持以事件、人物或全局总览作为工作台锚点进入统一图谱视图。
- 图谱工作台现在支持 URL 驱动的节点聚焦、统一节点检查器，以及 `/api/v1/graph/nodes/{node_type}/{node_id}` 节点详情接口，可直接沿邻接节点和时间上下文继续导航。
- 图谱工作台现在也支持事件参与者增删、事件/人物关系增删改的内联治理，常见图谱修正不再必须跳回独立校对页。
- 图谱工作台现在加入了时间主干 rail 和 `全部 / 事件 / 人物 / 时间主干` 视图切换，人物时间线与事件网络可以在同一工作区里来回切换。
- 图谱工作台现已补齐骨架屏、空状态、移动端焦点强调和内联校验提示，日常浏览与轻量治理的可用性明显更稳定。
- 图谱工作台现在支持连线聚焦，边也能作为一等交互对象被查看和快速切换两端节点，图谱感比单纯节点列表更强。

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
- New read-heavy APIs should prefer query services over route-level query composition.
- The `web` dev container stays on `NODE_ENV=development`, but production build verification must override to `NODE_ENV=production`.

## Verification Baseline

Verified on `2026-04-21`:

- `python3 -m compileall server/app server/tests server/scripts`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api alembic upgrade head`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T web sh -lc 'NODE_ENV=production npm run build'`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python scripts/e2e_api_flow.py --phase full --job-timeout-seconds 240`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/api/test_openapi_contracts.py`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extraction_run_service.py tests/api/test_openapi_contracts.py`
- `docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest tests/services/test_extraction_run_service.py tests/services/test_asset_text_service.py tests/services/test_local_media_service.py`
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
- Core write endpoints should use explicit Pydantic request schemas and forbid undeclared body fields.
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
