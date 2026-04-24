"""Shared chatbot constants."""

DEFAULT_CANDIDATES_APPLICATIONS_JOIN = (
    "FROM candidates c INNER JOIN applications a ON a.candidate_id = c.id"
)

CANDIDATES_SCHEMA = (
    """
TABLE candidates (
  id                  INTEGER PRIMARY KEY,
  organization_id     INTEGER NOT NULL,
  import_session_id   INTEGER,
  full_name           VARCHAR(255),
  email               VARCHAR(320),
  date_of_birth       DATE,
  created_at          TIMESTAMPTZ
)

TABLE applications (
  id                              INTEGER PRIMARY KEY,
  candidate_id                    INTEGER NOT NULL,  -- -> candidates.id
  import_session_id               INTEGER,
  notice_period                   VARCHAR(100),
  applied_at                      TIMESTAMPTZ,
  current_address                 TEXT,
  nationality                     VARCHAR(100),
  number_of_dependents            SMALLINT,
  religion_sect                   VARCHAR(100),
  has_transportation              transportation_availability,  -- PostgreSQL enum: yes | no | only_open_for_remote_opportunities
  applied_position                VARCHAR(255),
  applied_position_location       VARCHAR(255),
  is_open_for_relocation          relocation_openness,  -- PostgreSQL enum: yes | no | for_missions_only
  years_of_experience             NUMERIC(4,1),
  is_employed                     BOOLEAN,
  current_salary                  NUMERIC(12,2),
  expected_salary_remote          NUMERIC(12,2),
  expected_salary_onsite          NUMERIC(12,2),
  is_overtime_flexible            BOOLEAN,
  is_contract_flexible            BOOLEAN,
  tech_stack                      JSONB,   -- array of strings e.g. ["Python","React"]
  custom_fields                   JSONB,   -- org-specific extra fields
  created_at                      TIMESTAMPTZ,
  updated_at                      TIMESTAMPTZ,

  residency_type_id               INTEGER,  -- -> lookup_option
  marital_status_id               INTEGER,  -- -> lookup_option
  passport_validity_status_id     INTEGER,  -- -> lookup_option
  workplace_type_id               INTEGER,  -- -> lookup_option
  employment_type_id              INTEGER,  -- -> lookup_option
  education_level_id              INTEGER,  -- -> lookup_option
  education_completion_status_id  INTEGER   -- -> lookup_option
)

REQUIRED JOIN for application fields (position, salary, experience, tech_stack, address, lookups):
  """
    + DEFAULT_CANDIDATES_APPLICATIONS_JOIN
    + """

The legacy table name "candidate" (singular) is rejected at query execution — only "candidates" + "applications" (and related tables below) are allowed.

Aliases (use consistently):
  c = candidates (profile: full_name, email, organization_id, dates)
  a = applications (job application row: position, salary, tech_stack, etc.)

Row shape for listings:
  Prefer SELECT c.*, a.id AS application_id so rows include profile + application columns.
  The bare id from c.* is the candidate id; application_id is applications.id.

Counts:
  COUNT(*) counts application rows. For "how many candidates (people)" use COUNT(DISTINCT c.id).

Multiple applications per person:
  Optional: DISTINCT ON (c.id) ... ORDER BY c.id, a.created_at DESC for latest application only.

Subqueries:
  Repeat the same JOIN with new aliases (e.g. FROM candidates c2 INNER JOIN applications a2 ON a2.candidate_id = c2.id).

Nationality / country:
  Prefer a.nationality ILIKE for nationality text. Legacy rows may only have JSON in a.custom_fields.

TABLE lookup_option (
  id              INTEGER PRIMARY KEY,
  category_id     INTEGER,
  organization_id INTEGER,
  code            VARCHAR(100),   -- e.g. 'remote', 'full_time', 'bachelor'
  label           VARCHAR(255)    -- e.g. 'Remote', 'Full-Time', 'Bachelor'
)

TABLE lookup_category (
  id    INTEGER PRIMARY KEY,
  code  VARCHAR(100),   -- e.g. 'workplace_type', 'employment_type', 'education_level'
  label VARCHAR(255)
)

TABLE candidate_stage_comment (
  id               INTEGER PRIMARY KEY,
  candidate_id     INTEGER NOT NULL,  -- -> candidates.id
  organization_id  INTEGER NOT NULL,
  stage_key        VARCHAR(64),       -- pre_screening | technical_interview | hr_interview | offer_stage
  entries          JSONB,             -- array of {"text": "...", "created_at": "ISO-8601"} oldest->newest
  updated_at       TIMESTAMPTZ
)

TABLE candidate_resume (
  id               INTEGER PRIMARY KEY,
  candidate_id     INTEGER NOT NULL UNIQUE,  -- -> candidates.id (one resume per candidate)
  organization_id  INTEGER NOT NULL,
  filename         VARCHAR(255),
  content_type     VARCHAR(100),
  resume_info      JSONB   -- GPT-extracted structured data; keys: full_name, email, phone, summary,
                           --   skills (array of strings), languages (array), certifications (array),
                           --   work_experience (array of {company, title, start_date, end_date, description}),
                           --   education (array of {institution, degree, field_of_study, start_date, end_date})
)
"""
).strip()
