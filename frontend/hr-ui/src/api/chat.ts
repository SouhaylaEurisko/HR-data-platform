import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type {
  ChatResponse,
  Conversation,
  ConversationWithMessages,
  SendMessageRequest,
  SendMessageResponse,
} from '../types/api';

/**
 * Legacy: plain chat endpoint (kept for backward compatibility).
 */
export const sendChatMessage = async (message: string): Promise<ChatResponse> => {
  const response = await apiClient.post<ChatResponse>(API_ENDPOINTS.chat, { message });
  return response.data;
};

/**
 * Conversations API
 */
export const listConversations = async (): Promise<Conversation[]> => {
  const response = await apiClient.get<Conversation[]>(API_ENDPOINTS.conversations.list);
  return response.data;
};

export const getConversationById = async (
  id: number
): Promise<ConversationWithMessages> => {
  const response = await apiClient.get<ConversationWithMessages>(
    API_ENDPOINTS.conversations.getById(id)
  );
  return response.data;
};

export const sendConversationMessage = async (
  payload: SendMessageRequest
): Promise<SendMessageResponse> => {
  const response = await apiClient.post<SendMessageResponse>(
    API_ENDPOINTS.conversations.send,
    payload
  );
  return response.data;
};

export const deleteConversation = async (id: number): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.conversations.delete(id));
};