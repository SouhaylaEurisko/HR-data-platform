-- Add expected_salary and expected_salary_currency, remove religion from candidate table.
-- Run against your database, e.g.: psql -U your_user -d hr_project_database -f alter_candidate_expected_salary.sql

ALTER TABLE candidate
  ADD COLUMN IF NOT EXISTS expected_salary NUMERIC(12, 2),
  ADD COLUMN IF NOT EXISTS expected_salary_currency VARCHAR(10);

CREATE INDEX IF NOT EXISTS ix_candidate_expected_salary ON candidate (expected_salary);

ALTER TABLE candidate DROP COLUMN IF EXISTS religion;
