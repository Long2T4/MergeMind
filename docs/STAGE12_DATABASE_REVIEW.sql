-- PROPOSAL ONLY: Coordinate with the Stage 13 owner and incorporate into
-- one ordered Alembic revision. DO NOT run against shared Supabase unreviewed.
-- Existing local users are not automatically assigned to a Supabase account
-- based solely on an email match. Explicit verified linking is needed.
ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_user_id VARCHAR(36);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_auth_user_id ON users (auth_user_id);
-- No migration for review_issues.status: it already exists.
-- No timestamped issue-history analytics in this stage.
