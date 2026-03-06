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
  // Import endpoints
  importXlsx: `${API_BASE_URL}/api/import/xlsx`,
  previewXlsx: `${API_BASE_URL}/api/import/xlsx/preview`,
  
  // Candidate endpoints
  candidates: `${API_BASE_URL}/api/candidates`,
  candidateById: (id: number) => `${API_BASE_URL}/api/candidates/${id}`,
  
  // Chat endpoint
  chat: `${API_BASE_URL}/api/chat`,
  
  // Health check
  health: `${API_BASE_URL}/health`,
} as const;
