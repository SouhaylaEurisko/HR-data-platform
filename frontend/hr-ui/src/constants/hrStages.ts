import type { HrStageCommentEntry } from '../types/api';

/**
 * HR pipeline stages — keys must match backend `HR_STAGE_KEYS` / stage comment API.
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

export function emptyHrStageCommentLists(): Record<HrStageKey, HrStageCommentEntry[]> {
  return {
    pre_screening: [],
    technical_interview: [],
    hr_interview: [],
    offer_stage: [],
  };
}

/** Latest entry (API lists are oldest → newest). */
export function latestStageComment(
  entries: HrStageCommentEntry[] | undefined
): HrStageCommentEntry | undefined {
  if (!entries?.length) return undefined;
  return entries[entries.length - 1];
}
