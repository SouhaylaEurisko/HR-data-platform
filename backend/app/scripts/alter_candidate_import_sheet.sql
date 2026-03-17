-- Add import_sheet to candidate to store the Excel sheet name each row was imported from.
-- Run against your database, e.g.: psql -U your_user -d hr_project_database -f alter_candidate_import_sheet.sql

ALTER TABLE candidate
  ADD COLUMN IF NOT EXISTS import_sheet VARCHAR(255) NULL;
