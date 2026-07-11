# Operations Guide

## Goal

Capture the minimum operational workflow for backup, restore, verification, and incident handling.

## Local Stack Commands

```bash
docker compose -f deploy/compose/docker-compose.dev.yml up --build -d
docker compose -f deploy/compose/docker-compose.dev.yml ps
docker compose -f deploy/compose/docker-compose.dev.yml logs api --tail=200
docker compose -f deploy/compose/docker-compose.dev.yml logs worker --tail=200
```

## Frontend Dev Runtime Recovery

The local `web` service mounts `.next-dev` as a dedicated container volume for Next.js dev speed. Production builds use a separate `.next-build` output directory, so the active dev server no longer shares chunk artifacts with `next build`. The dev compose command still clears the mounted dev cache on startup, so a clean web recreation is the preferred recovery step:

```bash
docker compose -f deploy/compose/docker-compose.dev.yml up -d --no-deps --force-recreate --renew-anon-volumes web
```

When scripting local frontend smoke checks from Python on macOS, build the HTTP opener with proxies disabled or prefer `127.0.0.1`; system proxy settings may otherwise route `localhost` through a local proxy and report a false 502.

## Backup

### PostgreSQL

Create a logical backup:

```bash
docker compose -f deploy/compose/docker-compose.dev.yml exec -T postgres \
  pg_dump -U outlawer -d outlawer > backup-outlawer.sql
```

### MinIO

For local Docker development, preserve the `minio_data` volume or copy objects out through the MinIO client.

Recommended pattern:

1. export objects from the bucket
2. snapshot the PostgreSQL database
3. store both artifacts with the same timestamp

## Restore

### PostgreSQL

```bash
cat backup-outlawer.sql | docker compose -f deploy/compose/docker-compose.dev.yml exec -T postgres \
  psql -U outlawer -d outlawer
```

### After Restore

Run verification:

```bash
python3 server/scripts/e2e_api_flow.py --phase full
curl -sS http://localhost:8000/api/v1/health
curl -I http://localhost:3000
```

The full API e2e flow creates assets, notes, jobs, projections, events, entities, derivatives, and object-storage files with a unique `E2E-...` marker and removes those records in a `finally` cleanup step. If the process is killed before cleanup runs, search for the marker printed in the failing run or inspect recent titles beginning with `E2E-` before treating them as real data.

## Migration Verification

Use a clean environment whenever schema changes are introduced:

```bash
docker compose -f deploy/compose/docker-compose.dev.yml down -v
docker compose -f deploy/compose/docker-compose.dev.yml up --build -d
docker compose -f deploy/compose/docker-compose.dev.yml logs migrate --tail=200
```

## Failure Triage

When the async pipeline is unhealthy, inspect these first:

1. `docker compose -f deploy/compose/docker-compose.dev.yml logs api --tail=200`
2. `docker compose -f deploy/compose/docker-compose.dev.yml logs worker --tail=200`
3. `docker compose -f deploy/compose/docker-compose.dev.yml logs rabbitmq --tail=200`
4. `docker compose -f deploy/compose/docker-compose.dev.yml logs postgres --tail=200`

For product-level triage, open `/operations` in the web app. The operations console now summarizes:

- failed and active jobs
- reviewable extraction drafts
- pending entity/event merge candidates
- graph-governance activity now includes relation before/after diff summaries, and graph conflicts can expose direct canonical-relation removal actions when a real `relation_id` is available
- recent review and curation actions
- routing links into note detail, review, and curation pages

## Release Smoke Checklist

1. `docker compose -f deploy/compose/docker-compose.prod.yml config` succeeds.
2. migration job runs before API and worker.
3. `python3 server/scripts/e2e_api_flow.py --phase full` passes against the target environment.
4. `python3 server/scripts/e2e_manual_collection_flow.py` passes when Phase 31–34 workflows are in release scope.
5. homepage and API health endpoint return success.
