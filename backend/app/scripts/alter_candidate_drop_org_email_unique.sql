-- Allow multiple candidate rows per organization + email (separate applications / positions).
-- Run: psql -U your_user -d your_db -f alter_candidate_drop_org_email_unique.sql

ALTER TABLE candidate DROP CONSTRAINT IF EXISTS uq_candidate_org_email;
