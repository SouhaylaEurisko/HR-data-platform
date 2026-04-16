import apiClient from './client';
import { API_ENDPOINTS } from '../config';

export interface LookupOptionRow {
  id: number;
  code: string;
  label: string;
  display_order: number;
  is_active: boolean;
}

export async function getLookupOptions(
  categoryCode: string,
  orgId?: number
): Promise<LookupOptionRow[]> {
  const response = await apiClient.get<LookupOptionRow[]>(
    API_ENDPOINTS.lookupsByCategory(categoryCode),
    { params: orgId != null ? { org_id: orgId } : {} }
  );
  return response.data;
}
