/**
 * HR pipeline stages — keys and labels must match backend HR_STAGES / CandidateHrCommentUpdate.
 */
export const HR_STAGE_DEFS = [
  { key: 'pre_screening', label: 'Pre Screening' },
  { key: 'technical_interview', label: 'Technical Interview' },
  { key: 'hr_interview', label: 'HR Interview' },
  { key: 'offer_stage', label: 'Offer Stage' },
] as const;

export type HrStageKey = (typeof HR_STAGE_DEFS)[number]['key'];

/** One row from {@link HR_STAGE_DEFS} (for typed `.map` / `.find`). */
export type HrStageDef = (typeof HR_STAGE_DEFS)[number];

export function emptyHrStageComments(): Record<HrStageKey, string> {
  return {
    pre_screening: '',
    technical_interview: '',
    hr_interview: '',
    offer_stage: '',
  };
}
