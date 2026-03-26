import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { AnalyticsOverview } from '../types/api';

export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  const response = await apiClient.get<AnalyticsOverview>(API_ENDPOINTS.analyticsOverview);
  return response.data;
}
