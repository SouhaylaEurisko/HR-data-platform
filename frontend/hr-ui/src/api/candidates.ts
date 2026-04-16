import apiClient from './client';
import { API_ENDPOINTS } from '../config';
import type {
  ApplicationStatus,
  Candidate,
  CandidateListResponse,
  CandidateListParams,
  CandidateResume,
  RelocationOpenness,
  TransportationAvailability,
} from '../types/api';
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

export type CandidatePersonalPatchBody = {
  full_name?: string | null;
  email?: string | null;
  date_of_birth?: string | null;
  nationality?: string | null;
  current_address?: string | null;
  residency_type_id?: number | null;
  marital_status_id?: number | null;
  number_of_dependents?: number | null;
  religion_sect?: string | null;
  passport_validity_status_id?: number | null;
  has_transportation?: TransportationAvailability | null;
};

export type CandidateProfessionalPatchBody = {
  applied_position?: string | null;
  applied_position_location?: string | null;
  is_open_for_relocation?: RelocationOpenness | null;
  years_of_experience?: number | null;
  is_employed?: boolean | null;
  current_salary?: number | null;
  expected_salary_remote?: number | null;
  expected_salary_onsite?: number | null;
  notice_period?: string | null;
  is_overtime_flexible?: boolean | null;
  is_contract_flexible?: boolean | null;
  workplace_type_id?: number | null;
  employment_type_id?: number | null;
  tech_stack?: string[] | null;
  education_level_id?: number | null;
  education_completion_status_id?: number | null;
};

export const patchCandidatePersonal = async (
  id: number,
  body: CandidatePersonalPatchBody,
  orgId?: number
): Promise<Candidate> => {
  const response = await apiClient.patch<Candidate>(API_ENDPOINTS.candidatePersonal(id), body, {
    params: orgId != null ? { org_id: orgId } : {},
  });
  return response.data;
};

export const patchCandidateProfessional = async (
  id: number,
  body: CandidateProfessionalPatchBody,
  orgId?: number
): Promise<Candidate> => {
  const response = await apiClient.patch<Candidate>(API_ENDPOINTS.candidateProfessional(id), body, {
    params: orgId != null ? { org_id: orgId } : {},
  });
  return response.data;
};

export const deleteCandidate = async (id: number, orgId?: number): Promise<void> => {
  await apiClient.delete(API_ENDPOINTS.candidateById(id), {
    params: orgId != null ? { org_id: orgId } : {},
  });
};

export const getResume = async (candidateId: number): Promise<CandidateResume> => {
  const response = await apiClient.get<CandidateResume>(API_ENDPOINTS.candidateResume(candidateId));
  return response.data;
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
