import type { Candidate, ResumeInfo } from '../types/api';

function normalizeName(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, ' ');
}

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

export type ResumeIdentityMismatch = {
  nameMismatch: boolean;
  emailMismatch: boolean;
  cvName?: string;
  cvEmail?: string;
  candidateName?: string;
  candidateEmail?: string;
};

/**
 * When both CV extract and candidate record have a value for name (or email),
 * they must match after normalization. If either side is missing, that field is skipped.
 */
export function getResumeCandidateIdentityMismatch(
  candidate: Pick<Candidate, 'full_name' | 'email'>,
  resumeInfo: ResumeInfo | null | undefined,
): ResumeIdentityMismatch | null {
  const ri = resumeInfo ?? {};
  const cvName = typeof ri.full_name === 'string' ? ri.full_name.trim() : '';
  const cvEmail = typeof ri.email === 'string' ? ri.email.trim() : '';
  const candName = (candidate.full_name ?? '').trim();
  const candEmail = (candidate.email ?? '').trim();

  let nameMismatch = false;
  if (cvName && candName && normalizeName(cvName) !== normalizeName(candName)) {
    nameMismatch = true;
  }

  let emailMismatch = false;
  if (cvEmail && candEmail && normalizeEmail(cvEmail) !== normalizeEmail(candEmail)) {
    emailMismatch = true;
  }

  if (!nameMismatch && !emailMismatch) {
    return null;
  }

  return {
    nameMismatch,
    emailMismatch,
    cvName: cvName || undefined,
    cvEmail: cvEmail || undefined,
    candidateName: candName || undefined,
    candidateEmail: candEmail || undefined,
  };
}

export function formatResumeMismatchMessage(m: ResumeIdentityMismatch): string {
  const lines: string[] = [
    'The uploaded CV does not appear to match this candidate.',
    '',
  ];
  if (m.nameMismatch) {
    lines.push(`Name — candidate: ${m.candidateName ?? '—'}; CV: ${m.cvName ?? '—'}`);
  }
  if (m.emailMismatch) {
    lines.push(`Email — candidate: ${m.candidateEmail ?? '—'}; CV: ${m.cvEmail ?? '—'}`);
  }
  lines.push('', 'Please confirm you uploaded the correct file for this person.');
  return lines.join('\n');
}
