-- Empty all application data for fresh testing.
-- Run with: psql -U ai-team -d hr_project_database -f backend/app/scripts/clear_data.sql
-- Or use: python -m app.scripts.clear_data (from backend dir, uses .env DATABASE_URL)

-- Order: truncate tables that reference others first, then roots.
-- RESTART IDENTITY resets auto-increment so next IDs start at 1.
-- CASCADE truncates any tables with FK references to these (none outside this app).

TRUNCATE TABLE
  messages,
  conversation,
  candidate,
  import_session,
  custom_field_definition,
  lookup_option,
  user_account,
  lookup_category,
  organization
RESTART IDENTITY
CASCADE;
