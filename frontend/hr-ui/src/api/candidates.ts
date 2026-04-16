import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type {
  ApplicationStatus,
  Candidate,
  CandidateApplicationStatusResponse,
  CandidateHrStageCommentsUpdateResponse,
  CandidateListParams,
  CandidateProfileListResponse,
  CandidateProfilePatchResponse,
  CandidateResume,
  CandidateUpdatePayload,
} from '../types/api';
import type { HrStageKey } from '../constants/hrStages';

/**
 * Get a list of candidates with optional filters
 */
export const getCandidates = async (
  params?: CandidateListParams
): Promise<CandidateProfileListResponse> => {
  const response = await apiClient.get<CandidateProfileListResponse>(
    API_ENDPOINTS.candidates,
    { params: params ?? {} }
  );
  return response.data;
};

/**
 * Get a single candidate by ID
 */
export const getCandidateById = async (id: number): Promise<Candidate> => {
  const response = await apiClient.get<Candidate>(API_ENDPOINTS.candidateById(id));
  return response.data;
};

export const postCandidateHrStageComment = async (
  id: number,
  body: { stage: HrStageKey; text: string }
): Promise<CandidateHrStageCommentsUpdateResponse> => {
  const response = await apiClient.post<CandidateHrStageCommentsUpdateResponse>(
    API_ENDPOINTS.candidateHrStageComments(id),
    body
  );
  return response.data;
};

export const patchCandidateApplicationStatus = async (
  id: number,
  application_status: ApplicationStatus
): Promise<CandidateApplicationStatusResponse> => {
  const response = await apiClient.patch<CandidateApplicationStatusResponse>(
    API_ENDPOINTS.candidateApplicationStatus(id),
    { application_status }
  );
  return response.data;
};

export const getResume = async (candidateId: number): Promise<CandidateResume | null> => {
  const response = await apiClient.get<CandidateResume>(API_ENDPOINTS.candidateResume(candidateId));
  if (response.status === 204) {
    return null;
  }
  const data = response.data as CandidateResume | null | undefined;
  if (data == null || data === '') {
    return null;
  }
  return data;
};

export const uploadResume = async (candidateId: number, file: File): Promise<CandidateResume> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<CandidateResume>(
    API_ENDPOINTS.candidateResume(candidateId),
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  );
  return response.data;
};

export const downloadResume = async (candidateId: number): Promise<Blob> => {
  const response = await apiClient.get(API_ENDPOINTS.candidateResumeDownload(candidateId), {
    responseType: 'blob',
  });
  return response.data as Blob;
};

export const deleteResume = async (candidateId: number): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.candidateResume(candidateId));
};

export const patchCandidate = async (
  id: number,
  body: CandidateUpdatePayload,
  orgId = 1
): Promise<CandidateProfilePatchResponse> => {
  const response = await apiClient.patch<CandidateProfilePatchResponse>(
    API_ENDPOINTS.candidateById(id),
    body,
    {
      params: { org_id: orgId },
    }
  );
  return response.data;
};

export const deleteCandidate = async (id: number, orgId = 1): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.candidateById(id), { params: { org_id: orgId } });
};
