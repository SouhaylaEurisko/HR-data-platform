/**
 * TypeScript types matching the backend API schemas
 */

/** Matches PostgreSQL enum relocation_openness / backend RelocationOpenness. */
export type RelocationOpenness = 'yes' | 'no' | 'for_missions_only';

/** Matches PostgreSQL enum transportation_availability / backend TransportationAvailability. */
export type TransportationAvailability =
  | 'yes'
  | 'no'
  | 'only_open_for_remote_opportunities';

/** Matches backend ApplicationStatus. */
export type ApplicationStatus = 'pending' | 'on_hold' | 'rejected' | 'selected';

/** Same-email sibling application (detail API only). */
export interface RelatedApplicationSummary {
  id: number;
  applied_position: string | null;
  applied_at: string | null;
  created_at: string;
}

/** One timestamped HR note for a pipeline stage (append-only). */
export interface HrStageCommentEntry {
  id: number;
  text: string;
  created_at: string;
}

/** HR notes per pipeline stage: chronological list (oldest → newest). */
export interface HrStageComments {
  pre_screening: HrStageCommentEntry[];
  technical_interview: HrStageCommentEntry[];
  hr_interview: HrStageCommentEntry[];
  offer_stage: HrStageCommentEntry[];
}

export interface Candidate {
  id: number;
  organization_id: number;
  import_session_id: number | null;
  applied_at: string | null;

  // Personal
  full_name: string | null;
  email: string | null;
  date_of_birth: string | null;
  nationality: string | null;
  current_address: string | null;
  residency_type_id: number | null;
  marital_status_id: number | null;
  number_of_dependents: number | null;
  religion_sect: string | null;
  passport_validity_status_id: number | null;
  has_transportation: TransportationAvailability | null;

  // Professional
  applied_position: string | null;
  applied_position_location: string | null;
  is_open_for_relocation: RelocationOpenness | null;
  years_of_experience: number | null;
  is_employed: boolean | null;
  current_salary: number | null;
  expected_salary_remote: number | null;
  expected_salary_onsite: number | null;
  notice_period: string | null;
  is_overtime_flexible: boolean | null;
  is_contract_flexible: boolean | null;
  workplace_type_id: number | null;
  employment_type_id: number | null;
  tech_stack: string[];
  education_level_id: number | null;
  education_completion_status_id: number | null;

  // Dynamic & Raw
  custom_fields: Record<string, any>;
  raw_import_data: Record<string, any> | null;

  /** HR notes by pipeline stage (UI only; never from file import) */
  hr_stage_comments: HrStageComments;

  /** HR application outcome (UI only); null until HR sets it */
  application_status: ApplicationStatus | null;

  // Audit
  created_at: string;
  updated_at: string;

  // Import source (from import_session when loaded)
  import_filename?: string | null;
  import_sheet?: string | null;

  // Resolved lookup labels (populated by service layer)
  residency_type_label?: string | null;
  marital_status_label?: string | null;
  passport_validity_status_label?: string | null;
  workplace_type_label?: string | null;
  employment_type_label?: string | null;
  education_level_label?: string | null;
  education_completion_status_label?: string | null;

  /** Set on GET candidate by id when email is present (grouped applications). */
  application_index?: number | null;
  application_total?: number | null;
  related_applications?: RelatedApplicationSummary[];
}

// Resume types
export interface ResumeWorkExperience {
  company: string | null;
  title: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface ResumeEducation {
  institution: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface ResumeInfo {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  summary?: string | null;
  skills?: string[];
  languages?: string[];
  work_experience?: ResumeWorkExperience[];
  education?: ResumeEducation[];
  certifications?: string[];
}

export interface CandidateResume {
  id: number;
  candidate_id: number;
  organization_id: number;
  filename: string;
  content_type: string;
  resume_info: ResumeInfo;
  created_at: string;
  updated_at: string;
}

export interface CandidateListResponse {
  items: Candidate[];
  total: number;
  page: number;
  page_size: number;
}

/** Matches GET /api/candidates query params (name search, position, sort). */
export interface CandidateListParams {
  page?: number;
  page_size?: number;
  org_id?: number;
  search?: string;
  applied_position?: string;
  sort_by?: 'created_at' | 'expected_salary_remote' | 'expected_salary_onsite' | 'years_of_experience' | 'full_name' | 'applied_position';
  sort_order?: 'asc' | 'desc';
}

/** Matches GET /api/analytics/overview (org from JWT). */
export interface AnalyticsNamedCount {
  name: string;
  count: number;
}

export interface AnalyticsFilterOption {
  value: string;
  label: string;
  count: number;
}

export interface AnalyticsFilterOptions {
  statuses: AnalyticsFilterOption[];
  positions: AnalyticsFilterOption[];
  locations: AnalyticsFilterOption[];
}

export interface AnalyticsAppliedFilters {
  status: string | null;
  position: string | null;
  location: string | null;
}

export interface AnalyticsOverviewParams {
  status?: string;
  position?: string;
  location?: string;
}

export interface AnalyticsPositionAverage {
  name: string;
  average: number;
  sample_count: number;
}

export interface AnalyticsOverview {
  total_candidates: number;
  by_application_status: AnalyticsNamedCount[];
  top_applied_positions: AnalyticsNamedCount[];
  top_locations: AnalyticsNamedCount[];
  avg_expected_salary_by_position: AnalyticsPositionAverage[];
  avg_years_experience_by_position: AnalyticsPositionAverage[];
  candidates_with_resume: number;
  resume_coverage_percent: number;
  recent_applications_30d: number;
  filter_options: AnalyticsFilterOptions;
  applied_filters: AnalyticsAppliedFilters;
}

export interface CustomFieldDefinition {
  id: number;
  field_key: string;
  label: string;
  field_type: string;
}

// Column mapping types for two-phase import
export interface ColumnMapping {
  excel_header: string;
  db_column: string | null;
  db_column_label: string | null;
  confidence: number;
  source: 'programmatic' | 'llm' | 'unmatched';
}

export interface AvailableColumn {
  value: string;
  label: string;
}

export interface AnalyzeResponse {
  session_id: number;
  filename: string;
  sheets: string[];
  matched_columns: ColumnMapping[];
  suggested_columns: ColumnMapping[];
  unmatched_columns: ColumnMapping[];
  available_columns: AvailableColumn[];
  already_mapped: string[];
}

export interface ConfirmImportRequest {
  session_id: number;
  confirmed_mappings: Record<string, string>;
  new_custom_fields: Array<{ header: string; label: string }>;
  skip_columns: string[];
  sheet_names: string[];
  org_id: number;
}

export interface ImportResult {
  session_id: number;
  status: string;
  total_created: number;
  total_skipped_empty_rows: number;
  total_skipped_duplicates: number;
  total_errors: number;
  sheet_results: SheetResult[];
  row_errors: Array<{ row_index: number; error: string; sheet?: string }>;
}

export interface SheetResult {
  sheet_name: string;
  created: number;
  skipped_empty: number;
  skipped_duplicates: number;
  row_errors: Array<{ row_index: number; error: string }>;
}

export interface SheetPreview {
  name: string;
  max_row: number;
  data_rows: number;
}

export interface XlsxPreviewResponse {
  file_name: string;
  sheets: SheetPreview[];
  total_sheets: number;
}

// Lookup types
export interface LookupOption {
  id: number;
  code: string;
  label: string;
  display_order: number;
  is_active: boolean;
}

export interface LookupCategory {
  id: number;
  code: string;
  label: string;
  description: string | null;
  is_system: boolean;
}

// Chat types
export interface ChatRequest {
  message: string;
}

export interface AgentResponseData {
  intent: string;
  summary: string | null;
  total_found: number | null;
  sql: string | null;
  explanation: string | null;
  candidates?: Record<string, any>[];
  stats?: Record<string, any>[];
}

export type ChatResponse = AgentResponseData;

// Authentication types
export interface User {
  id: number;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  organization_id: number;
  role: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

// Conversation types
export interface ConversationMessage {
  id: number;
  conversation_id: number;
  content: string;
  sender: 'user' | 'assistant';
  created_at: string;
  response?: AgentResponseData | null;
}

export interface Conversation {
  id: number;
  title?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: ConversationMessage[];
}

export interface SendMessageRequest {
  content: string;
  sender: 'user' | 'assistant';
  conversation_id?: number;
}

export interface SendMessageResponse {
  reply: string;
  conversation_id: number;
  response?: AgentResponseData | null;
}
