import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { LookupOption } from '../types/api';

export async function fetchLookupOptions(
  categoryCode: string,
  orgId = 1
): Promise<LookupOption[]> {
  const response = await apiClient.get<LookupOption[]>(API_ENDPOINTS.lookupsByCategory(categoryCode), {
    params: { org_id: orgId },
  });
  return response.data;
}
