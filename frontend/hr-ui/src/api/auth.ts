import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { AuthResponse, User } from '../types/api';

export interface SignupRequest {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  organization_id?: number;
  role?: string;
}

export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const formData = new FormData();
  // FastAPI OAuth2PasswordRequestForm expects "username" field
  formData.append('username', email);
  formData.append('password', password);

  const response = await apiClient.post<AuthResponse>(
    API_ENDPOINTS.auth.login,
    formData,
    {
      headers: {
        // Let the browser set appropriate multipart headers
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
};

export const signup = async (payload: SignupRequest): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>(
    API_ENDPOINTS.auth.signup,
    payload
  );
  return response.data;
};

export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>(API_ENDPOINTS.auth.me);
  return response.data;
};