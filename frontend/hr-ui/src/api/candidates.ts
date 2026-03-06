import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type {
  Candidate,
  CandidateListResponse,
  CandidateListParams,
} from '../types/api';

/**
 * Get a list of candidates with optional filters
 */
export const getCandidates = async (
  params?: CandidateListParams
): Promise<CandidateListResponse> => {
  const response = await apiClient.get<CandidateListResponse>(
    API_ENDPOINTS.candidates,
    { params }
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
