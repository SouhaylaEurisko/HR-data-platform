import type { RelocationOpenness } from '../types/api';

const LABELS: Record<RelocationOpenness, string> = {
  yes: 'Yes',
  no: 'No',
  for_missions_only: 'For missions only',
};

/** Human-readable label for API enum value `is_open_for_relocation`. */
export function relocationOpennessLabel(
  value: RelocationOpenness | string | null | undefined,
): string {
  if (value == null || value === '') return '—';
  if (value in LABELS) return LABELS[value as RelocationOpenness];
  return String(value);
}
