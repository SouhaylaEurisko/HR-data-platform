import type { ApplicationStatus } from '../types/api';

export const APPLICATION_STATUS_VALUES: readonly ApplicationStatus[] = [
  'pending',
  'on_hold',
  'rejected',
  'selected',
];

export const APPLICATION_STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: 'pending', label: 'Pending' },
  { value: 'on_hold', label: 'On hold' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'selected', label: 'Selected' },
];

/** API → UI: null/unknown means no status set yet (no default to pending). */
export function parseApplicationStatus(
  raw: string | null | undefined
): ApplicationStatus | null {
  if (raw == null || typeof raw !== 'string') return null;
  const s = raw.trim().toLowerCase();
  if (!s) return null;
  return (APPLICATION_STATUS_VALUES as readonly string[]).includes(s)
    ? (s as ApplicationStatus)
    : null;
}

export function applicationStatusLabel(status: ApplicationStatus): string {
  return APPLICATION_STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status;
}
