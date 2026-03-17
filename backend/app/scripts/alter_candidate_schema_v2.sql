-- Candidate table schema changes:
-- - first_name -> full_name (single name field)
-- - Remove last_name, phone
-- - notice_period_days -> notice_period (VARCHAR, value as in Excel)
-- - employment_status_id -> is_employed (BOOLEAN from "are you employed?" in Excel)
--
-- Run: psql -U ai-team -d hr_project_database -f backend/app/scripts/alter_candidate_schema_v2.sql

-- 1. Add new columns
ALTER TABLE candidate
  ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
  ADD COLUMN IF NOT EXISTS notice_period VARCHAR(100),
  ADD COLUMN IF NOT EXISTS is_employed BOOLEAN;

-- 2. Migrate first_name (+ last_name if present) into full_name before dropping
UPDATE candidate
SET full_name = TRIM(CONCAT(COALESCE(first_name, ''), ' ', COALESCE(last_name, '')))
WHERE full_name IS NULL AND (first_name IS NOT NULL OR last_name IS NOT NULL);

-- 3. Copy notice_period_days to notice_period as text (e.g. "30 days") for existing rows
UPDATE candidate
SET notice_period = (notice_period_days::TEXT || ' days')
WHERE notice_period IS NULL AND notice_period_days IS NOT NULL;

-- 4. Drop old columns
ALTER TABLE candidate
  DROP COLUMN IF EXISTS first_name,
  DROP COLUMN IF EXISTS last_name,
  DROP COLUMN IF EXISTS phone,
  DROP COLUMN IF EXISTS notice_period_days,
  DROP COLUMN IF EXISTS employment_status_id;

-- 5. Index for full_name search/sort
CREATE INDEX IF NOT EXISTS ix_candidate_full_name ON candidate (full_name);
