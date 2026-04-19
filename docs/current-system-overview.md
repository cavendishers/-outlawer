# Current System Overview

Last updated: `2026-04-19`

## Purpose

This document records the current end-to-end shape of the online AI-assisted knowledge base: how users move through the product, how data moves through the system, how processing transforms raw inputs into graph views, and which capabilities are already implemented or still missing.

## Overall Product Flow

```mermaid
flowchart TD
    A["User opens Web UI"] --> B["Login with username and password"]
    B --> C["Inbox: upload or paste content"]
    C --> D{"Input type"}
    D -->|Text| E["Persist original text asset"]
    D -->|Image| F["Persist raw image in MinIO"]
    D -->|Audio| G["Persist raw audio in MinIO"]
    D -->|Video| H["Persist raw video in MinIO"]
    E --> I["Create note and enqueue processing job"]
    F --> I
    G --> I
    H --> I
    I --> J["Worker extracts normalized text and structured knowledge"]
    J --> K["Persist canonical note, entities, events, relations, timeline, embeddings, style views"]
    K --> L["Browse library, people, events, timeline, search, story views"]
    L --> M["Review merge candidates"]
    L --> N["Curate event graph records"]
    M --> K
    N --> K
```

## Runtime Service Flow

```mermaid
flowchart LR
    Browser["Next.js Web"] --> API["FastAPI /api/v1"]
    API --> PG["PostgreSQL + pgvector"]
    API --> MinIO["MinIO raw object storage"]
    API --> Redis["Redis cache/support"]
    API --> Rabbit["RabbitMQ broker"]
    Rabbit --> Worker["Celery worker"]
    Worker --> MinIO
    Worker --> PG
    Worker --> OpenRouter["OpenRouter AI models"]
    Worker --> LocalMedia["Local OCR/ASR fallback: tesseract, ffmpeg, vosk"]
```

## Data Flow

```mermaid
flowchart TD
    Raw["Raw asset<br/>text/image/audio/video"] --> RawStore["raw_assets + MinIO object"]
    RawStore --> Derivative["asset_derivatives<br/>OCR / transcript / video scene evidence / normalized text"]
    Derivative --> Note["notes + note_chunks<br/>canonical searchable text"]
    Note --> Extraction["extraction_runs + extraction_evidence<br/>versioned AI output"]
    Extraction --> Entity["entities + entity_aliases + note_entities"]
    Extraction --> Event["events + event_entities + note_events"]
    Extraction --> Relation["relations"]
    Extraction --> Timeline["timeline_items"]
    Extraction --> Embedding["embeddings"]
    Extraction --> Story["style_views"]
    Entity --> Views["People index / entity story / review / curation"]
    Event --> Views2["Event detail / timeline / graph / event curation"]
    Relation --> Graph["Graph views and related-event navigation"]
    Timeline --> Graph
    Embedding --> Search["Unified keyword/entity/event/similarity search"]
    Story --> StoryViews["Chunibyo-style note and entity pages"]
```

## Data Processing Flow

```mermaid
sequenceDiagram
    participant Web as Web UI
    participant API as FastAPI
    participant DB as PostgreSQL
    participant MQ as RabbitMQ
    participant Worker as Celery Worker
    participant Object as MinIO
    participant AI as OpenRouter / Local Fallback

    Web->>API: Upload content or create asset
    API->>Object: Store raw file when needed
    API->>DB: Insert raw asset and job metadata
    API->>MQ: Enqueue processing task
    Worker->>DB: Load job and raw asset metadata
    Worker->>Object: Read raw file when needed
    Worker->>AI: Extract normalized text and structured graph payload
    Worker->>DB: Persist note, extraction run, entities, events, relations, timeline, embeddings, style views
    Worker->>DB: Mark job completed or failed
    Web->>API: Poll job / browse result views
    API->>DB: Query canonical and derived read models
    API-->>Web: Return library, people, event, timeline, search, review, curation data
```

## Implemented Capabilities

- `DONE`: Docker Compose development deployment with PostgreSQL, pgvector, RabbitMQ, Redis, MinIO, API, worker, web, and migration job.
- `DONE`: Alembic migration workflow and release smoke guidance.
- `DONE`: Username/password login with bearer-token auth.
- `DONE`: Raw text, image, audio, and video asset ingestion with raw preservation.
- `DONE`: Image OCR, audio transcription, and video derivative text fallback using local tools.
- `DONE`: Async job tracking and retry flow through Celery and RabbitMQ.
- `DONE`: Note canonicalization, extraction-run persistence, and reprocessing entry point.
- `DONE`: Extraction run history, per-run summary retrieval, and side-by-side diff snapshots for note reprocessing review.
- `DONE`: Historical extraction runs can now be re-applied to the current note projection as an explicit rollback/replay action.
- `DONE`: Entity, event, relation, note-link, timeline, and extraction-evidence persistence.
- `DONE`: OpenRouter text extraction with free-model fallback batching and local heuristic fallback.
- `DONE`: Multimodal derivative enrichment now combines local OCR/ASR parsing with optional OpenRouter enhancement and source attribution snippets.
- `DONE`: Video derivatives now preserve sampled scene time ranges and label direct OCR/ASR evidence separately from model-inferred context.
- `DONE`: Embedding-backed similarity search, merge-candidate generation, and unified search page.
- `DONE`: People index, library, event pages, timeline/global graph view, note detail, and story views.
- `DONE`: Chunibyo-style note and entity story views stored separately from canonical data.
- `DONE`: Merge review queue with accept/reject, entity merge, event merge, alias confirmation, and audit history.
- `DONE`: Event curation page and API for event fields, participants, and event-centered relation add/update/remove.
- `DONE`: Entity curation page and API for canonical/display fields, type, status, seen timestamps, alias governance, and entity-centered relation maintenance.
- `DONE`: Current visual token system and brutalist page styling pass.

## Unimplemented Or Partial Capabilities By Priority

1. `HIGH`: Multimodal quality upgrade is still incomplete. The pipeline now preserves local parsing, AI enhancement, source attribution, and video scene evidence together, but image semantics and speaker/context extraction are still MVP-grade.
2. `HIGH`: Extraction replay and version comparison. Run history, side-by-side extraction diffs, and manual historical re-apply now exist, but draft replay approval and explicit rollback audit workflow are not complete.
3. `MEDIUM`: Back-office operations dashboard. Job monitoring, failed-task retry center, raw asset management, and extraction-run inspection still require developer-level visibility.
4. `MEDIUM`: Strongly typed API contracts across all public endpoints. Some endpoints still accept generic dictionaries and should move toward explicit request/response schemas.
5. `MEDIUM`: Dedicated read-model query service layer. Several route files still compose read data directly instead of using dedicated query services.
6. `LOW`: Collaboration and permissions. Current implementation is single-user/workspace oriented.
7. `LOW`: Plugin and integration system for external importers and third-party sync.
8. `LOW`: Mobile-first ingestion and browsing experience.

## Next Development Direction

The next implementation slice should continue multimodal understanding quality work, now focusing on non-video semantic depth and better extraction replay controls. The expected scope is:

- strengthen image semantic extraction beyond OCR-only signals
- improve audio speaker/context extraction
- version multimodal prompts and normalize richer derivative payloads
- add draft replay approval and rollback audit controls before applying new projections
