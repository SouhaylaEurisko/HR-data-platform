import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { ChatRequest, ChatResponse } from '../types/api';

/**
 * Send a chat message and get candidate search results
 */
export const sendChatMessage = async (
  message: string
): Promise<ChatResponse> => {
  const response = await apiClient.post<ChatResponse>(
    API_ENDPOINTS.chat,
    { message } as ChatRequest
  );
  return response.data;
};
