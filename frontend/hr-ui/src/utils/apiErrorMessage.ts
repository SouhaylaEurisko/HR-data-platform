/** Best-effort message from axios-style or Error rejects (no `any`). */
export function apiErrorMessage(err: unknown, fallback: string): string {
  if (err && typeof err === 'object') {
    const o = err as {
      response?: { data?: { detail?: unknown } };
      message?: string;
    };
    const detail = o.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail)) {
      return detail.map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).join(', ');
    }
    if (typeof o.message === 'string' && o.message) return o.message;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}
