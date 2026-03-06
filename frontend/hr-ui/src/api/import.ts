import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { ImportXlsxResponse } from '../types/api';

export interface SheetPreview {
  name: string;
  max_row: number;
  data_rows: number;
}

export interface XlsxPreviewResponse {
  file_name: string;
  sheets: SheetPreview[];
  total_sheets: number;
}

/**
 * Preview an XLSX file structure without importing
 */
export const previewXlsx = async (file: File): Promise<XlsxPreviewResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<XlsxPreviewResponse>(
    API_ENDPOINTS.previewXlsx,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};

/**
 * Upload and import an XLSX file
 * @param file - The XLSX file to import
 * @param sheetNames - Optional: specific sheet names to import
 * @param importAllSheets - Optional: import all sheets in the workbook
 */
export const importXlsx = async (
  file: File,
  sheetNames?: string[],
  importAllSheets?: boolean
): Promise<ImportXlsxResponse> => {
  const formData = new FormData();
  formData.append('file', file);

  // Build query parameters
  const params = new URLSearchParams();
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
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
};
