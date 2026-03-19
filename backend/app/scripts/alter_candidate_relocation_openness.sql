-- Replace boolean is_open_for_relocation with PostgreSQL enum (yes | no | for_missions_only).
-- Run: psql -U your_user -d your_db -f alter_candidate_relocation_openness.sql

CREATE TYPE relocation_openness AS ENUM ('yes', 'no', 'for_missions_only');

ALTER TABLE candidate
  ALTER COLUMN is_open_for_relocation TYPE relocation_openness
  USING (
    CASE
      WHEN is_open_for_relocation IS TRUE THEN 'yes'::relocation_openness
      WHEN is_open_for_relocation IS FALSE THEN 'no'::relocation_openness
      ELSE NULL
    END
  );
