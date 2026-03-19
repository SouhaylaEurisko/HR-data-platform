-- Application status for HR workflow (nullable until HR sets it).
-- Run: psql -U your_user -d your_db -f alter_candidate_application_status.sql

ALTER TABLE candidate
  ADD COLUMN IF NOT EXISTS application_status VARCHAR(32);

CREATE INDEX IF NOT EXISTS ix_candidate_application_status ON candidate (application_status);

COMMENT ON COLUMN candidate.application_status IS 'HR application outcome; set via UI only; NULL = unset.';

-- If the column already existed as NOT NULL with a default, allow NULL:
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'candidate'
      AND column_name = 'application_status' AND is_nullable = 'NO'
  ) THEN
    ALTER TABLE candidate ALTER COLUMN application_status DROP DEFAULT;
    ALTER TABLE candidate ALTER COLUMN application_status DROP NOT NULL;
  END IF;
END $$;
