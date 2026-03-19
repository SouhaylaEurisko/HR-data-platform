/**
 * Backend API configuration
 * 
 * The backend URL is loaded from environment variables.
 * In development, it defaults to http://127.0.0.1:8000
 * 
 * To change it, create a .env file in the root of this project with:
 * VITE_API_BASE_URL=http://your-backend-url:port
 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export const API_ENDPOINTS = {
  // Authentication endpoints
  auth: {
    login: `${API_BASE_URL}/api/auth/login`,
    signup: `${API_BASE_URL}/api/auth/signup`,
    me: `${API_BASE_URL}/api/auth/me`,
  },
  
  // Import endpoints (two-phase: preview → analyze → confirm)
  previewXlsx: `${API_BASE_URL}/api/import/xlsx/preview`,
  analyzeXlsx: `${API_BASE_URL}/api/import/xlsx/analyze`,
  confirmImport: `${API_BASE_URL}/api/import/xlsx/confirm`,

  // Lookup endpoints
  lookups: `${API_BASE_URL}/api/lookups`,
  lookupsByCategory: (code: string) => `${API_BASE_URL}/api/lookups/${code}`,

  // Custom field definitions (for filter UI)
  customFields: `${API_BASE_URL}/api/custom-fields`,

  // Candidate endpoints
  candidates: `${API_BASE_URL}/api/candidates`,
  candidateById: (id: number) => `${API_BASE_URL}/api/candidates/${id}`,
  candidateHrComment: (id: number) => `${API_BASE_URL}/api/candidates/${id}/hr-comment`,
  candidateApplicationStatus: (id: number) =>
    `${API_BASE_URL}/api/candidates/${id}/application-status`,
  
  // Chat endpoint
  chat: `${API_BASE_URL}/api/chat`,
  
  // Conversations endpoints
  conversations: {
    list: `${API_BASE_URL}/api/conversations`,
    getById: (id: number) => `${API_BASE_URL}/api/conversations/${id}`,
    send: `${API_BASE_URL}/api/conversations/send`,
    delete: (id: number) => `${API_BASE_URL}/api/conversations/${id}`,
  },
  
  // Health check
  health: `${API_BASE_URL}/health`,
} as const;