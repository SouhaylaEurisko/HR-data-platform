import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { CustomFieldDefinition } from '../types/api';

export const getCustomFieldDefinitions = async (
  orgId: number = 1
): Promise<CustomFieldDefinition[]> => {
  const response = await apiClient.get<CustomFieldDefinition[]>(
    API_ENDPOINTS.customFields,
    { params: { org_id: orgId } }
  );
  return response.data;
};
