import type { ApplicationStatus } from '../types/api';
import { applicationStatusLabel } from '../constants/applicationStatus';
import './ApplicationStatusBadge.css';

export default function ApplicationStatusBadge({
  status,
  size = 'default',
  className = '',
}: {
  status: ApplicationStatus | null;
  size?: 'default' | 'large';
  className?: string;
}) {
  if (status == null) return null;

  const sizeClass = size === 'large' ? ' application-status-badge--large' : '';

  return (
    <span
      className={`application-status-badge application-status-badge--${status}${sizeClass} ${className}`.trim()}
    >
      {applicationStatusLabel(status)}
    </span>
  );
}
