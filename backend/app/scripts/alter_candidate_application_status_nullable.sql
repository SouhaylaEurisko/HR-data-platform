-- Migrate existing application_status column to nullable with no default (idempotent).
-- Use if you already ran alter_candidate_application_status.sql with NOT NULL DEFAULT.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'candidate'
      AND column_name = 'application_status'
  ) THEN
    ALTER TABLE candidate ALTER COLUMN application_status DROP DEFAULT;
    ALTER TABLE candidate ALTER COLUMN application_status DROP NOT NULL;
  END IF;
END $$;
