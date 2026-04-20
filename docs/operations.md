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
- recent review and curation actions
- routing links into note detail, review, and curation pages

## Release Smoke Checklist

1. `docker compose -f deploy/compose/docker-compose.prod.yml config` succeeds.
2. migration job runs before API and worker.
3. `python3 server/scripts/e2e_api_flow.py --phase full` passes against the target environment.
4. homepage and API health endpoint return success.
