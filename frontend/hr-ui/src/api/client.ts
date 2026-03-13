import axios from 'axios';
import type { AxiosInstance, AxiosError } from 'axios';
import { API_BASE_URL } from '../config';

/**
 * Axios instance configured for the HR Platform API
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

// Request interceptor - adds auth token to all requests
apiClient.interceptors.request.use(
  (config) => {
    // Get token from localStorage (same key used in AuthContext)
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Handle common errors
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const data = error.response.data as any;
      
      // Handle 401 Unauthorized - token expired or invalid
      if (status === 401) {
        const errorDetail = data?.detail || 'Authentication failed';
        console.error('Authentication Error:', errorDetail);
        
        // Clear invalid token from localStorage
        const token = localStorage.getItem('auth_token');
        if (token) {
          console.warn('Clearing invalid token from storage');
          localStorage.removeItem('auth_token');
          
          // If we're not already on the login page, redirect to login
          if (window.location.pathname !== '/login') {
            // Only redirect if we have a valid token that failed (not a missing token)
            if (errorDetail.includes('expired') || errorDetail.includes('validate')) {
              window.location.href = '/login?expired=true';
            }
          }
        }
      }
      
      switch (status) {
        case 400:
          console.error('Bad Request:', data?.detail || 'Invalid request');
          break;
        case 404:
          console.error('Not Found:', data?.detail || 'Resource not found');
          break;
        case 500:
          console.error('Server Error:', data?.detail || 'Internal server error');
          break;
        default:
          console.error(`Error ${status}:`, data?.detail || 'An error occurred');
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('Network Error: No response from server. Is the backend running?');
    } else {
      // Something else happened
      console.error('Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;