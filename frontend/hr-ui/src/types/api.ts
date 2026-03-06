/**
 * TypeScript types matching the backend API schemas
 */

export interface Candidate {
  id: number;
  source_file: string | null;
  source_sheet: string | null;
  source_table_index: number | null;
  row_index: number | null;
  full_name: string | null;
  email: string | null;
  nationality: string | null;
  date_of_birth: string | null; // ISO date string
  position: string | null;
  expected_salary: number | null;
  // Text representation of expected salary (e.g., ranges like "1800-2000")
  expected_salary_text?: string | null;
  years_experience: number | null;
  notice_period: string | null;
  current_address: string | null;
  raw_data: Record<string, any> | null;
  created_at: string; // ISO datetime string
  updated_at: string; // ISO datetime string
}

export interface CandidateListResponse {
  items: Candidate[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChatSearchFilters {
  position: string | null;
  min_expected_salary: number | null;
  max_expected_salary: number | null;
  min_years_experience: number | null;
  max_years_experience: number | null;
  nationality: string | null;
  current_address: string | null;
}

export interface ChatRequest {
  message: string;
}

export interface AggregationResult {
  total_count: number | null;
  avg_salary: number | null;
  avg_experience: number | null;
  min_salary: number | null;
  max_salary: number | null;
  min_experience: number | null;
  max_experience: number | null;
}

export interface ChatResponse {
  reply: string;
  filters: ChatSearchFilters;
  total_matches: number;
  top_candidates: Candidate[];
  aggregations: AggregationResult | null;
}

export interface TableResult {
  table_index: number;
  start_row: number;
  end_row: number | null;
  created: number;
  skipped_empty_rows: number;
  skipped_duplicates: number;
  row_errors: Array<{
    row_index: number;
    error: string;
  }>;
}

export interface SheetResult {
  sheet_name: string;
  tables_found?: number;
  created: number;
  skipped_empty_rows: number;
  skipped_duplicates: number;
  row_errors: Array<{
    row_index: number;
    error: string;
    sheet?: string;
  }>;
  table_results?: TableResult[];
}

export interface ImportXlsxResponse {
  file_name: string;
  sheets_processed?: string[]; // New: list of processed sheets
  total_created?: number; // New: total across all sheets
  total_skipped_empty_rows?: number; // New: total across all sheets
  total_skipped_duplicates?: number; // New: total across all sheets
  sheet_results?: SheetResult[]; // New: per-sheet results
  // Legacy fields (for backward compatibility)
  created?: number;
  skipped_empty_rows?: number;
  skipped_duplicates?: number;
  row_errors?: Array<{
    row_index: number;
    error: string;
    sheet?: string;
  }>;
}

export interface CandidateListParams {
  page?: number;
  page_size?: number;
  nationality?: string;
  date_of_birth?: string;
  position?: string;
  expected_salary?: number;
  current_address?: string;
  min_years_experience?: number;
  max_years_experience?: number;
  search?: string;
  sort_by?: 'created_at' | 'expected_salary' | 'years_experience';
  sort_order?: 'asc' | 'desc';
}
