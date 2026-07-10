"""bind legacy relation evidence to first-class relation ids

Revision ID: 20260711_01
Revises: 20260518_01
"""

from alembic import op


revision = "20260711_01"
down_revision = "20260518_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older projections stored the relation source object id in
    # extraction_evidence.target_id. Only unambiguous matches are rewritten;
    # ambiguous legacy evidence remains readable through the existing fallback.
    op.execute(
        """
        WITH candidates AS (
            SELECT
                evidence.id AS evidence_id,
                MIN(relation.id) AS relation_id,
                COUNT(*) AS match_count
            FROM extraction_evidence AS evidence
            JOIN relations AS relation
              ON relation.user_id = evidence.user_id
             AND relation.source_id = evidence.target_id
             AND relation.relation_type = evidence.field_name
            WHERE evidence.target_type = 'relation'
            GROUP BY evidence.id
        )
        UPDATE extraction_evidence AS evidence
           SET target_id = candidates.relation_id
          FROM candidates
         WHERE evidence.id = candidates.evidence_id
           AND candidates.match_count = 1
        """
    )


def downgrade() -> None:
    # Relation ids are the corrected identity and cannot be mapped back to a
    # source object id after a relation has been edited or removed.
    pass
