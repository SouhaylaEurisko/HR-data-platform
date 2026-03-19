import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type {
  ApplicationStatus,
  Candidate,
  CandidateListResponse,
  CandidateListParams,
  HrStageComments,
} from '../types/api';

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

export const patchCandidateHrComment = async (
  id: number,
  hr_stage_comments: HrStageComments
): Promise<Candidate> => {
  const response = await apiClient.patch<Candidate>(API_ENDPOINTS.candidateHrComment(id), {
    pre_screening: hr_stage_comments.pre_screening,
    technical_interview: hr_stage_comments.technical_interview,
    hr_interview: hr_stage_comments.hr_interview,
    offer_stage: hr_stage_comments.offer_stage,
  });
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
