# MVP Plan

## Scope

The first release should prioritize a working knowledge pipeline rather than exhaustive features.

## Must-Have Features

- username and password login
- text, image, and audio ingestion
- raw asset persistence
- async AI processing with job tracking
- note generation from assets
- entity extraction
- event extraction
- timeline view support
- similarity search support
- chunibyo-style story view generation

## Deferred Features

- advanced permissions
- collaboration
- mobile app
- graph database
- plugin system
- full video pipeline if delivery pressure is high

## Recommended Build Order

1. set up FastAPI project structure
2. add auth and `users`
3. add Alembic and base migrations
4. add MinIO-backed `raw_assets`
5. add `notes` and `ai_jobs`
6. add Celery with RabbitMQ
7. add extraction pipeline for entities and events
8. add timeline projection
9. add search and embeddings
10. add story views
11. build initial Next.js pages

## First Frontend Pages

- `/login`
- `/inbox`
- `/library`
- `/notes/[id]`
- `/people`
- `/events`
- `/timeline`
- `/story/note/[id]`
- `/story/entity/[id]`
