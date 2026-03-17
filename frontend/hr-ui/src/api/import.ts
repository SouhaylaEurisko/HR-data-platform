import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type {
  ImportXlsxResponse,
  XlsxPreviewResponse,
  AnalyzeResponse,
  ConfirmImportRequest,
  ImportResult,
} from '../types/api';

/**
 * Preview an XLSX file structure without importing
 */
export const previewXlsx = async (file: File): Promise<XlsxPreviewResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<XlsxPreviewResponse>(
    API_ENDPOINTS.previewXlsx,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return response.data;
};

/**
 * Phase A: Analyze an XLSX file and get column mapping suggestions
 */
export const analyzeXlsx = async (
  file: File,
  sheetNames?: string[],
  importAllSheets?: boolean,
  orgId: number = 1,
  userId: number = 1,
): Promise<AnalyzeResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const params = new URLSearchParams();
  params.append('org_id', String(orgId));
  params.append('user_id', String(userId));
  if (importAllSheets) {
    params.append('import_all_sheets', 'true');
  } else if (sheetNames && sheetNames.length > 0) {
    sheetNames.forEach(name => params.append('sheet_names', name));
  }

  const url = `${API_ENDPOINTS.analyzeXlsx}?${params.toString()}`;

  const response = await apiClient.post<AnalyzeResponse>(
    url,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return response.data;
};

/**
 * Phase B: Confirm column mappings and import
 */
export const confirmImport = async (
  body: ConfirmImportRequest,
): Promise<ImportResult> => {
  const response = await apiClient.post<ImportResult>(
    API_ENDPOINTS.confirmImport,
    body,
  );
  return response.data;
};

/**
 * One-shot upload and import (backward compatible)
 */
export const importXlsx = async (
  file: File,
  sheetNames?: string[],
  importAllSheets?: boolean,
  orgId: number = 1,
  userId: number = 1,
): Promise<ImportXlsxResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const params = new URLSearchParams();
  params.append('org_id', String(orgId));
  params.append('user_id', String(userId));
  if (importAllSheets) {
    params.append('import_all_sheets', 'true');
  } else if (sheetNames && sheetNames.length > 0) {
    sheetNames.forEach(name => params.append('sheet_names', name));
  }

  const url = params.toString()
    ? `${API_ENDPOINTS.importXlsx}?${params.toString()}`
    : API_ENDPOINTS.importXlsx;

  const response = await apiClient.post<ImportXlsxResponse>(
    url,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return response.data;
};
