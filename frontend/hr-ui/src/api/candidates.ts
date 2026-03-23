import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type { ApplicationStatus, Candidate, CandidateListResponse, CandidateListParams } from '../types/api';
import type { HrStageKey } from '../constants/hrStages';

/**
 * Get a list of candidates with optional filters
 */
export const getCandidates = async (
  params?: CandidateListParams
): Promise<CandidateListResponse> => {
  const response = await apiClient.get<CandidateListResponse>(
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
): Promise<Candidate> => {
  const response = await apiClient.post<Candidate>(API_ENDPOINTS.candidateHrStageComments(id), body);
  return response.data;
};

export const patchCandidateApplicationStatus = async (
  id: number,
  application_status: ApplicationStatus
): Promise<Candidate> => {
  const response = await apiClient.patch<Candidate>(
    API_ENDPOINTS.candidateApplicationStatus(id),
    { application_status }
  );
  return response.data;
};
