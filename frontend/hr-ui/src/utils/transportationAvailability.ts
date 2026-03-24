import type { TransportationAvailability } from '../types/api';

const LABELS: Record<TransportationAvailability, string> = {
  yes: 'YES',
  no: 'NO',
  only_open_for_remote_opportunities: 'Only Open for Remote Opportunities',
};

/** Human-readable label for API enum value `has_transportation`. */
export function transportationAvailabilityLabel(
  value: TransportationAvailability | string | null | undefined,
): string {
  if (value == null || value === '') return '—';
  if (value in LABELS) return LABELS[value as TransportationAvailability];
  return String(value);
}
