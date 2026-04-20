"""phase a source-of-truth cleanup"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from app.utils.text import normalize_name

revision = "20260420_04"
down_revision = "20260418_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)

    entities = sa.table(
        "entities",
        sa.column("id", sa.String(length=36)),
        sa.column("display_name", sa.String(length=255)),
        sa.column("canonical_name", sa.String(length=255)),
        sa.column("alias_json", sa.JSON()),
    )
    entity_aliases = sa.table(
        "entity_aliases",
        sa.column("id", sa.String(length=36)),
        sa.column("entity_id", sa.String(length=36)),
        sa.column("alias", sa.String(length=255)),
        sa.column("normalized_alias", sa.String(length=255)),
        sa.column("alias_type", sa.String(length=32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    note_chunks = sa.table(
        "note_chunks",
        sa.column("id", sa.String(length=36)),
        sa.column("note_id", sa.String(length=36)),
        sa.column("embedding_vector", Vector(8)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    embeddings = sa.table(
        "embeddings",
        sa.column("id", sa.String(length=36)),
        sa.column("owner_type", sa.String(length=32)),
        sa.column("owner_id", sa.String(length=36)),
        sa.column("vector", Vector(8)),
        sa.column("model_name", sa.String(length=64)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    existing_alias_keys = {
        (row.entity_id, row.normalized_alias)
        for row in bind.execute(
            sa.select(entity_aliases.c.entity_id, entity_aliases.c.normalized_alias)
        ).mappings()
    }

    alias_inserts: list[dict[str, object]] = []
    for row in bind.execute(sa.select(entities)).mappings():
        reserved = {normalize_name(row["display_name"]), normalize_name(row["canonical_name"])}
        seen_for_entity = {
            normalized_alias
            for entity_id, normalized_alias in existing_alias_keys
            if entity_id == row["id"]
        }
        for raw_alias in row["alias_json"] or []:
            cleaned = str(raw_alias or "").strip()
            if not cleaned:
                continue
            normalized = normalize_name(cleaned)
            if not normalized or normalized in reserved or normalized in seen_for_entity:
                continue
            alias_inserts.append(
                {
                    "id": str(uuid4()),
                    "entity_id": row["id"],
                    "alias": cleaned,
                    "normalized_alias": normalized,
                    "alias_type": "backfill",
                    "created_at": now,
                    "updated_at": now,
                }
            )
            seen_for_entity.add(normalized)
            existing_alias_keys.add((row["id"], normalized))
    if alias_inserts:
        op.bulk_insert(entity_aliases, alias_inserts)

    existing_note_embeddings = {
        row.owner_id
        for row in bind.execute(
            sa.select(embeddings.c.owner_id).where(
                embeddings.c.owner_type == "note",
                embeddings.c.model_name == "heuristic-v1",
            )
        ).mappings()
    }
    note_embedding_inserts: list[dict[str, object]] = []
    for row in bind.execute(
        sa.select(
            note_chunks.c.note_id,
            note_chunks.c.embedding_vector,
            note_chunks.c.created_at,
            note_chunks.c.updated_at,
        ).where(note_chunks.c.embedding_vector.is_not(None))
    ).mappings():
        if row["note_id"] in existing_note_embeddings:
            continue
        note_embedding_inserts.append(
            {
                "id": str(uuid4()),
                "owner_type": "note",
                "owner_id": row["note_id"],
                "vector": row["embedding_vector"],
                "model_name": "heuristic-v1",
                "created_at": row["created_at"] or now,
                "updated_at": row["updated_at"] or row["created_at"] or now,
            }
        )
        existing_note_embeddings.add(row["note_id"])
    if note_embedding_inserts:
        op.bulk_insert(embeddings, note_embedding_inserts)

    op.execute(
        sa.text(
            """
            DELETE FROM entity_aliases
            WHERE id IN (
              SELECT id
              FROM (
                SELECT
                  id,
                  row_number() OVER (
                    PARTITION BY entity_id, normalized_alias
                    ORDER BY created_at ASC NULLS FIRST, id ASC
                  ) AS rn
                FROM entity_aliases
              ) ranked
              WHERE ranked.rn > 1
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM event_entities
            WHERE id IN (
              SELECT id
              FROM (
                SELECT
                  id,
                  row_number() OVER (
                    PARTITION BY event_id, entity_id
                    ORDER BY display_order ASC, created_at ASC NULLS FIRST, id ASC
                  ) AS rn
                FROM event_entities
              ) ranked
              WHERE ranked.rn > 1
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM embeddings
            WHERE id IN (
              SELECT id
              FROM (
                SELECT
                  id,
                  row_number() OVER (
                    PARTITION BY owner_type, owner_id, model_name
                    ORDER BY created_at ASC NULLS FIRST, id ASC
                  ) AS rn
                FROM embeddings
              ) ranked
              WHERE ranked.rn > 1
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM relations
            WHERE (
              relation_type = 'participates_in'
              AND (
                (source_type = 'entity' AND target_type = 'event')
                OR (source_type = 'event' AND target_type = 'entity')
              )
            )
            OR (
              source_type IN ('entity', 'event')
              AND target_type IN ('entity', 'event')
              AND meta_json ->> 'source' = 'curation_participant'
            )
            """
        )
    )

    op.create_unique_constraint(
        "uq_entity_aliases_entity_normalized",
        "entity_aliases",
        ["entity_id", "normalized_alias"],
    )
    op.create_unique_constraint(
        "uq_event_entities_event_entity",
        "event_entities",
        ["event_id", "entity_id"],
    )
    op.create_unique_constraint(
        "uq_embeddings_owner_model",
        "embeddings",
        ["owner_type", "owner_id", "model_name"],
    )
    op.drop_column("note_chunks", "embedding_vector")


def downgrade() -> None:
    op.add_column("note_chunks", sa.Column("embedding_vector", Vector(8), nullable=True))
    op.drop_constraint("uq_embeddings_owner_model", "embeddings", type_="unique")
    op.drop_constraint("uq_event_entities_event_entity", "event_entities", type_="unique")
    op.drop_constraint("uq_entity_aliases_entity_normalized", "entity_aliases", type_="unique")
