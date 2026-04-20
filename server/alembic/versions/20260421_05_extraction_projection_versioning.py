"""add extraction and projection versioning metadata"""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20260421_05"
down_revision = "20260420_04"
branch_labels = None
depends_on = None

ACTIVE_LINEAGE_STATUSES = {"applied", "superseded", "completed"}


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "extraction_runs",
        sa.Column("provider_name", sa.String(length=64), nullable=False, server_default="local"),
    )
    op.add_column(
        "extraction_runs",
        sa.Column("model_name", sa.String(length=255), nullable=False, server_default="heuristic_pipeline"),
    )
    op.add_column(
        "extraction_runs",
        sa.Column("prompt_version", sa.String(length=64), nullable=False, server_default="text-heuristic-v1"),
    )
    op.add_column(
        "extraction_runs",
        sa.Column("schema_version", sa.String(length=64), nullable=False, server_default="ai-extraction-format-v1"),
    )
    op.add_column(
        "extraction_runs",
        sa.Column("input_hash", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column("extraction_runs", sa.Column("parent_run_id", sa.String(length=36), nullable=True))
    op.add_column(
        "extraction_runs",
        sa.Column("run_kind", sa.String(length=32), nullable=False, server_default="initial"),
    )
    op.add_column(
        "extraction_runs",
        sa.Column("projection_status", sa.String(length=32), nullable=False, server_default="not_applied"),
    )
    op.create_index(op.f("ix_extraction_runs_parent_run_id"), "extraction_runs", ["parent_run_id"], unique=False)
    op.create_index(op.f("ix_extraction_runs_projection_status"), "extraction_runs", ["projection_status"], unique=False)
    op.create_foreign_key(
        "fk_extraction_runs_parent_run_id",
        "extraction_runs",
        "extraction_runs",
        ["parent_run_id"],
        ["id"],
    )

    op.create_table(
        "projection_versions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("note_id", sa.String(length=36), nullable=False),
        sa.Column("extraction_run_id", sa.String(length=36), nullable=False),
        sa.Column("source_asset_id", sa.String(length=36), nullable=True),
        sa.Column("previous_projection_id", sa.String(length=36), nullable=True),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_runs.id"]),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
        sa.ForeignKeyConstraint(["previous_projection_id"], ["projection_versions.id"]),
        sa.ForeignKeyConstraint(["source_asset_id"], ["raw_assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projection_versions_user_id"), "projection_versions", ["user_id"], unique=False)
    op.create_index(op.f("ix_projection_versions_note_id"), "projection_versions", ["note_id"], unique=False)
    op.create_index(
        op.f("ix_projection_versions_extraction_run_id"),
        "projection_versions",
        ["extraction_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_projection_versions_previous_projection_id"),
        "projection_versions",
        ["previous_projection_id"],
        unique=False,
    )

    op.add_column("notes", sa.Column("active_projection_id", sa.String(length=36), nullable=True))
    op.create_index(op.f("ix_notes_active_projection_id"), "notes", ["active_projection_id"], unique=False)
    op.create_foreign_key(
        "fk_notes_active_projection_id",
        "notes",
        "projection_versions",
        ["active_projection_id"],
        ["id"],
    )

    extraction_runs = sa.table(
        "extraction_runs",
        sa.column("id", sa.String(length=36)),
        sa.column("user_id", sa.String(length=36)),
        sa.column("note_id", sa.String(length=36)),
        sa.column("source_asset_id", sa.String(length=36)),
        sa.column("normalized_result_json", sa.JSON()),
        sa.column("status", sa.String(length=32)),
        sa.column("extractor_name", sa.String(length=128)),
        sa.column("extractor_version", sa.String(length=32)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("provider_name", sa.String(length=64)),
        sa.column("model_name", sa.String(length=255)),
        sa.column("prompt_version", sa.String(length=64)),
        sa.column("schema_version", sa.String(length=64)),
        sa.column("input_hash", sa.String(length=64)),
        sa.column("parent_run_id", sa.String(length=36)),
        sa.column("run_kind", sa.String(length=32)),
        sa.column("projection_status", sa.String(length=32)),
    )
    notes = sa.table(
        "notes",
        sa.column("id", sa.String(length=36)),
        sa.column("active_projection_id", sa.String(length=36)),
    )
    projection_versions = sa.table(
        "projection_versions",
        sa.column("id", sa.String(length=36)),
        sa.column("user_id", sa.String(length=36)),
        sa.column("note_id", sa.String(length=36)),
        sa.column("extraction_run_id", sa.String(length=36)),
        sa.column("source_asset_id", sa.String(length=36)),
        sa.column("previous_projection_id", sa.String(length=36)),
        sa.column("action_type", sa.String(length=32)),
        sa.column("summary_json", sa.JSON()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    run_rows = list(
        bind.execute(
            sa.select(
                extraction_runs.c.id,
                extraction_runs.c.user_id,
                extraction_runs.c.note_id,
                extraction_runs.c.source_asset_id,
                extraction_runs.c.normalized_result_json,
                extraction_runs.c.status,
                extraction_runs.c.extractor_name,
                extraction_runs.c.extractor_version,
                extraction_runs.c.created_at,
                extraction_runs.c.updated_at,
            ).order_by(
                extraction_runs.c.note_id.asc(),
                extraction_runs.c.created_at.asc(),
                extraction_runs.c.id.asc(),
            )
        ).mappings()
    )

    previous_run_id_by_note: dict[str, str] = {}
    lineage_runs_by_note: dict[str, list[dict[str, object]]] = {}

    for row in run_rows:
        note_id = str(row["note_id"])
        extractor_name = str(row["extractor_name"] or "heuristic_pipeline")
        extractor_version = str(row["extractor_version"] or "v1")
        provider_name = "openrouter" if extractor_name == "openrouter" else "local"
        model_name = extractor_version if extractor_name == "openrouter" else extractor_name
        prompt_version = "text-openrouter-v1" if extractor_name == "openrouter" else "text-heuristic-v1"
        schema_version = "ai-extraction-format-v1"
        input_hash = hashlib.sha256(_payload_text(row["normalized_result_json"]).encode("utf-8")).hexdigest()
        parent_run_id = previous_run_id_by_note.get(note_id)
        run_kind = "reprocess" if parent_run_id else "initial"
        projection_status = _projection_status_from_run_status(str(row["status"] or "completed"))

        bind.execute(
            sa.update(extraction_runs)
            .where(extraction_runs.c.id == row["id"])
            .values(
                provider_name=provider_name,
                model_name=model_name,
                prompt_version=prompt_version,
                schema_version=schema_version,
                input_hash=input_hash,
                parent_run_id=parent_run_id,
                run_kind=run_kind,
                projection_status=projection_status,
            )
        )
        previous_run_id_by_note[note_id] = str(row["id"])

        if str(row["status"] or "completed") in ACTIVE_LINEAGE_STATUSES:
            lineage_runs_by_note.setdefault(note_id, []).append(dict(row))

    projection_inserts: list[dict[str, object]] = []
    active_projection_by_note: dict[str, str] = {}
    projection_status_by_run_id: dict[str, str] = {}

    for note_id, lineage_runs in lineage_runs_by_note.items():
        previous_projection_id: str | None = None
        for index, row in enumerate(lineage_runs):
            projection_id = str(uuid4())
            is_last = index == len(lineage_runs) - 1
            projection_inserts.append(
                {
                    "id": projection_id,
                    "user_id": row["user_id"],
                    "note_id": row["note_id"],
                    "extraction_run_id": row["id"],
                    "source_asset_id": row["source_asset_id"],
                    "previous_projection_id": previous_projection_id,
                    "action_type": "backfill_projection_version",
                    "summary_json": _projection_summary(row["normalized_result_json"]),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )
            projection_status_by_run_id[str(row["id"])] = "applied" if is_last else "superseded"
            previous_projection_id = projection_id
            if is_last:
                active_projection_by_note[note_id] = projection_id

    if projection_inserts:
        op.bulk_insert(projection_versions, projection_inserts)

    for run_id, projection_status in projection_status_by_run_id.items():
        bind.execute(
            sa.update(extraction_runs)
            .where(extraction_runs.c.id == run_id)
            .values(projection_status=projection_status)
        )

    for note_id, projection_id in active_projection_by_note.items():
        bind.execute(
            sa.update(notes)
            .where(notes.c.id == note_id)
            .values(active_projection_id=projection_id)
        )


def downgrade() -> None:
    op.drop_constraint("fk_notes_active_projection_id", "notes", type_="foreignkey")
    op.drop_index(op.f("ix_notes_active_projection_id"), table_name="notes")
    op.drop_column("notes", "active_projection_id")

    op.drop_index(op.f("ix_projection_versions_previous_projection_id"), table_name="projection_versions")
    op.drop_index(op.f("ix_projection_versions_extraction_run_id"), table_name="projection_versions")
    op.drop_index(op.f("ix_projection_versions_note_id"), table_name="projection_versions")
    op.drop_index(op.f("ix_projection_versions_user_id"), table_name="projection_versions")
    op.drop_table("projection_versions")

    op.drop_constraint("fk_extraction_runs_parent_run_id", "extraction_runs", type_="foreignkey")
    op.drop_index(op.f("ix_extraction_runs_projection_status"), table_name="extraction_runs")
    op.drop_index(op.f("ix_extraction_runs_parent_run_id"), table_name="extraction_runs")
    op.drop_column("extraction_runs", "projection_status")
    op.drop_column("extraction_runs", "run_kind")
    op.drop_column("extraction_runs", "parent_run_id")
    op.drop_column("extraction_runs", "input_hash")
    op.drop_column("extraction_runs", "schema_version")
    op.drop_column("extraction_runs", "prompt_version")
    op.drop_column("extraction_runs", "model_name")
    op.drop_column("extraction_runs", "provider_name")


def _payload_text(payload: object) -> str:
    if isinstance(payload, dict):
        summary = payload.get("summary")
        if isinstance(summary, dict):
            canonical_text = str(summary.get("canonical_text") or "").strip()
            if canonical_text:
                return canonical_text
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return ""


def _projection_status_from_run_status(status: str) -> str:
    if status == "ready_for_review":
        return "pending_review"
    if status == "rejected":
        return "rejected"
    if status == "failed":
        return "failed"
    return "not_applied"


def _projection_summary(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    return {
        "title": str(summary.get("title") or ""),
        "category": str(summary.get("category") or ""),
        "entity_count": len(payload.get("entities")) if isinstance(payload.get("entities"), list) else 0,
        "event_count": len(events),
        "relation_count": len(payload.get("relations")) if isinstance(payload.get("relations"), list) else 0,
        "similarity_hint_count": len(payload.get("similarity_hints")) if isinstance(payload.get("similarity_hints"), list) else 0,
        "event_id": None,
    }
