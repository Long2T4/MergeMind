"""Store optional beginner explanations on review findings."""

import sqlalchemy as sa
from alembic import op

revision = "0007_beginner_explanations"
down_revision = "0006_review_analysis_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not op.get_context().as_sql:
        columns = sa.inspect(op.get_bind()).get_columns("review_issues")
        if any(column["name"] == "beginner_explanation" for column in columns):
            return
    op.add_column("review_issues", sa.Column("beginner_explanation", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("review_issues") as batch:
        batch.drop_column("beginner_explanation")
