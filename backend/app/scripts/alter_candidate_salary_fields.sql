-- Replace expected_salary, expected_salary_currency, current_salary_currency, preferred_contract_period_months
-- with expected_salary_remote and expected_salary_onsite.
-- Run against your database, e.g.: psql -U your_user -d hr_project_database -f alter_candidate_salary_fields.sql

-- Add new columns
ALTER TABLE candidate
  ADD COLUMN IF NOT EXISTS expected_salary_remote NUMERIC(12, 2) NULL,
  ADD COLUMN IF NOT EXISTS expected_salary_onsite NUMERIC(12, 2) NULL;

CREATE INDEX IF NOT EXISTS ix_candidate_expected_salary_remote ON candidate (expected_salary_remote);
CREATE INDEX IF NOT EXISTS ix_candidate_expected_salary_onsite ON candidate (expected_salary_onsite);

-- Drop old columns
ALTER TABLE candidate
  DROP COLUMN IF EXISTS expected_salary,
  DROP COLUMN IF EXISTS expected_salary_currency,
  DROP COLUMN IF EXISTS current_salary_currency,
  DROP COLUMN IF EXISTS preferred_contract_period_months;
