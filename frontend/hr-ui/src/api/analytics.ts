import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { AnalyticsOverview, AnalyticsOverviewParams } from '../types/api';

export async function getAnalyticsOverview(
  params: AnalyticsOverviewParams = {},
): Promise<AnalyticsOverview> {
  const response = await apiClient.get<AnalyticsOverview>(API_ENDPOINTS.analyticsOverview, {
    params: Object.fromEntries(
      Object.entries(params).filter(([_, value]) => value != null && value !== ''),
    ),
  });
  return response.data;
}
