# Deployment Plan

## Deployment Style

Use Docker Compose as the default deployment path for local development and the first production release.

Current verified local stack:

- compose file: `deploy/compose/docker-compose.dev.yml`
- web: `http://localhost:3000`
- api: `http://localhost:8000/api/v1`
- nginx: `http://localhost:8088`
- browser-facing web requests should use same-origin `/api/v1`, which the Next.js web container rewrites to the backend API service

## Containers

- `web`: Next.js application
- `api`: FastAPI service
- `worker`: Celery worker
- `postgres`: PostgreSQL with pgvector
- `rabbitmq`: message broker
- `redis`: cache and task support
- `minio`: object storage
- `nginx`: reverse proxy

## Directory Layout

```text
deploy/
  docker/
    web.Dockerfile
    api.Dockerfile
    worker.Dockerfile
    nginx.conf
  compose/
    docker-compose.dev.yml
    docker-compose.prod.yml
  env/
    web.env.example
    server.env.example
```

Production compose file:

- `deploy/compose/docker-compose.prod.yml`

## Environment Rules

- configuration must come from environment variables
- do not hardcode secrets
- keep `.env.example` files current
- local Docker development loads the repository root `.env` through compose `env_file`
- keep local secrets in `.env` and `server/.env`; both should remain uncommitted
- the dev `web` service must set `NODE_ENV=development`
- OpenRouter extraction is enabled with `EXTRACTOR_PROVIDER=openrouter` plus `OPENROUTER_API_KEY`
- OpenRouter free-model fallback uses `OPENROUTER_MODELS`; `OPENROUTER_MODEL` is prepended as the preferred first model when set
- OpenRouter allows at most three fallback models per request; the backend chunks longer free-model lists into three-model batches
- Bailian multimodal understanding is enabled with `VISION_PROVIDER=bailian`, `AUDIO_TRANSCRIPTION_PROVIDER=bailian`, and `BAILIAN_API_KEY`
- Bailian uses the OpenAI-compatible endpoint configured by `BAILIAN_BASE_URL`; default models are `BAILIAN_VISION_MODEL=qwen3.5-plus`, `BAILIAN_VIDEO_MODEL=qwen3.5-plus`, and `BAILIAN_AUDIO_MODEL=qwen3-omni-30b-a3b-captioner`
- dev `api` and `worker` images install `.[dev]`, so `python -m pytest` can run inside the `api` container after boot
- local OCR/ASR modules are legacy utilities; the main image/audio/video ingestion path now uses Bailian AI models and falls back only to metadata when the provider is unavailable

## Persistent Data

Use volumes for:

- PostgreSQL data
- RabbitMQ data
- Redis data if persistence is enabled
- MinIO data

## Startup Order

1. PostgreSQL
2. RabbitMQ
3. Redis
4. MinIO
5. migration job
6. API
7. worker
8. web
9. nginx

## Reverse Proxy

Recommended routing:

- `/` -> `web`
- `/api` -> `api`
- file delivery via MinIO signed URLs or a controlled media route

Current upload/read behavior:

- uploads are proxied through the API into MinIO
- raw asset reads return `original_text` for text assets or a presigned `raw_url` for file assets
- image, audio, and video assets can generate `asset_derivatives.normalized_text` locally before the knowledge extraction stage

## Production Rollout

Recommended sequence:

1. pull new images
2. start or verify dependencies
3. run database migration job
4. start API and worker
5. start web and nginx
6. verify health checks

Recommended preflight:

```bash
docker compose -f deploy/compose/docker-compose.prod.yml config
```

## Health Checks

At minimum add health checks for:

- API readiness
- PostgreSQL connectivity
- RabbitMQ broker connectivity
- MinIO availability
- worker liveness

## Verification Commands

```bash
docker compose -f deploy/compose/docker-compose.dev.yml up --build -d
docker compose -f deploy/compose/docker-compose.dev.yml ps
docker compose -f deploy/compose/docker-compose.dev.yml exec -T api python -m pytest
python3 server/scripts/e2e_api_flow.py --phase full
curl -I http://localhost:3000
docker compose -f deploy/compose/docker-compose.prod.yml config
```
