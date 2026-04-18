# Architecture Design

## Goal

Build an online, AI-assisted knowledge base inspired by Obsidian with:

- multimodal ingestion
- preserved raw materials
- asynchronous AI organization
- entity and event extraction
- timeline and relation-driven browsing
- stylized story rendering

## System Overview

The recommended architecture is a modular monorepo with a Python backend and Docker-first deployment.

```text
project/
  web/
  server/
  deploy/
  docs/
```

## Core Components

### Frontend

- Next.js
- TypeScript
- Tailwind CSS

Primary UI responsibilities:

- login
- asset upload
- inbox and processing status
- note detail pages
- entity index pages
- event pages
- timeline views
- stylized story views

### Backend API

- FastAPI
- SQLAlchemy 2.x
- Pydantic

Primary responsibilities:

- auth
- asset management
- note management
- entity and event querying
- search
- job tracking
- API-proxied file ingest handling
- stable response shaping through serializers or response schemas
- pagination and contract consistency for list endpoints

### Async Processing

- Celery workers
- RabbitMQ as broker
- Redis as cache and optional result backend
- OpenRouter as the LLM gateway for structured extraction when configured
- local OCR and ASR fallback inside the worker for multimodal parsing

Primary responsibilities:

- media preprocessing
- transcript and OCR pipelines
- knowledge extraction
- embedding generation
- relation building
- stylized story rendering

### Storage

- PostgreSQL for transactional data
- pgvector for embeddings
- MinIO for raw files and large derived artifacts
- Redis for cache and task support

## Data Layers

Keep these layers separate:

### Raw Layer

- original text
- audio
- image
- video
- original metadata

### Derived Layer

- transcript
- OCR output
- frame captions
- normalized text

### Knowledge Layer

- notes
- entities
- events
- relations
- timeline items
- embeddings

### Presentation Layer

- summaries
- timeline projections
- story views
- chunibyo-style text renderings

## Request and Processing Flow

1. User uploads an asset.
2. API stores metadata and file references.
3. API creates a note or processing request.
4. API creates an async job.
5. Worker consumes the job from RabbitMQ.
6. Worker generates derivative text if needed.
7. For image/audio/video assets, worker first attempts local parsing:
   - image: Tesseract OCR
   - audio: Vosk ASR
   - video: frame OCR plus audio transcription
8. If richer AI parsing is available, worker may enrich derivative text through OpenRouter.
9. Worker extracts entities, events, time, tags, and relations.
10. Worker stores raw extraction history in `extraction_runs`.
11. Worker upserts canonical entities, events, relations, timeline items, and embeddings.
12. Worker generates stylized story views.
13. Frontend reads progress and displays results.

## Recommended Server Layout

```text
server/
  app/
    api/
      serializers.py
    core/
    models/
    schemas/
    repositories/
    services/
    tasks/
    workers/
    utils/
  alembic/
  tests/
  scripts/
```

## Design Principles

- preserve source material
- keep AI work asynchronous
- avoid mixing canonical knowledge with stylized output
- optimize for Docker deployment
- enforce migration-based schema changes
- keep route handlers thin and move aggregation/query logic into services
- use serializers or response schemas instead of assembling ad hoc payloads in every route
- treat timeline and graph views as read projections over canonical knowledge

## Recommended Internal Boundaries

- route layer: request parsing, auth, status code mapping
- application services: ingestion, orchestration, writes
- query services: timeline, graph, search, index views
- serializers/presenters: stable API payloads

This keeps future graph, search, and multimodal iterations from leaking across every layer.
