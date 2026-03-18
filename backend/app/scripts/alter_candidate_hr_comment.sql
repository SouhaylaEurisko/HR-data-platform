-- HR-only notes per candidate; never populated by file import.
ALTER TABLE candidate ADD COLUMN IF NOT EXISTS hr_comment TEXT;

COMMENT ON COLUMN candidate.hr_comment IS 'Internal HR comment; set via UI only, not import.';
