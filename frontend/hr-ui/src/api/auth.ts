import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { AuthResponse, User } from '../types/api';

export interface CreateUserAdminRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role: 'hr_manager' | 'hr_viewer';
}

export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>(API_ENDPOINTS.auth.login, {
    email,
    password,
  });

  return response.data;
};

/** HR manager creates another user in the same org; does not issue a login token. */
export const createUserAsAdmin = async (
  payload: CreateUserAdminRequest
): Promise<User> => {
  const response = await apiClient.post<User>(API_ENDPOINTS.auth.users, payload);
  return response.data;
};

export const changePassword = async (
  currentPassword: string,
  newPassword: string
): Promise<void> => {
  await apiClient.post(API_ENDPOINTS.auth.changePassword, {
    current_password: currentPassword,
    new_password: newPassword,
  });
};

export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>(API_ENDPOINTS.auth.me);
  return response.data;
};

export const listUsers = async (): Promise<User[]> => {
  const response = await apiClient.get<User[]>(API_ENDPOINTS.auth.users);
  return response.data;
};

export const setUserActive = async (userId: number, isActive: boolean): Promise<User> => {
  const response = await apiClient.patch<User>(API_ENDPOINTS.auth.userStatus(userId), {
    is_active: isActive,
  });
  return response.data;
};