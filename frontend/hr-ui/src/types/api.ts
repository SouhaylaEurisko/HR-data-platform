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

export interface ChatRequest {
  message: string;
}

/**
 * New agent pipeline response shape.
 * Returned inside SendMessageResponse.response and ConversationMessage.response
 */
export interface AgentResponseData {
  intent: string;                        // "chitchat" | "filter" | "aggregation" | "filter_and_aggregation"
  summary: string | null;                // explanatory paragraph about results
  total_found: number | null;            // number of candidate rows returned
  sql: string | null;                    // generated SQL (debug)
  explanation: string | null;            // SQL explanation (debug)
  candidates?: Record<string, any>[];    // candidate rows (filter / filter_and_aggregation)
  stats?: Record<string, any>[];         // aggregation stats rows
}

// Keep ChatResponse for backward compat; alias to the new shape
export type ChatResponse = AgentResponseData;

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

// Authentication types
export interface User {
  id: number;
  email: string;
  full_name?: string | null;
  is_active?: boolean;
  created_at?: string; // ISO datetime string
  updated_at?: string; // ISO datetime string
}

export interface AuthResponse {
  access_token: string;
  token_type: string; // Usually "bearer"
  user?: User; // Optional user info in response
}

// Conversation types
export interface ConversationMessage {
  id: number;
  conversation_id: number;
  content: string;
  sender: 'user' | 'assistant';
  created_at: string; // ISO datetime string
  response?: AgentResponseData | null; // Agent pipeline response data
}

export interface Conversation {
  id: number;
  title?: string | null;
  created_at: string; // ISO datetime string
  updated_at?: string; // ISO datetime string
}

export interface ConversationWithMessages extends Conversation {
  messages: ConversationMessage[];
}

export interface SendMessageRequest {
  content: string;
  sender: 'user' | 'assistant';
  conversation_id?: number; // Optional: if provided, adds to existing conversation
}

export interface SendMessageResponse {
  reply: string;
  conversation_id: number;
  response?: AgentResponseData | null; // Agent pipeline response data
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