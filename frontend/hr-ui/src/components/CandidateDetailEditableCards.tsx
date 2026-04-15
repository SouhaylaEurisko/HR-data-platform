import { useState, useEffect } from 'react';
import { patchCandidate } from '../api/candidates';
import type {
  Candidate,
  CandidateProfilePatchResponse,
  CandidateUpdatePayload,
  LookupOption,
  RelocationOpenness,
  TransportationAvailability,
} from '../types/api';
import { apiErrorMessage } from '../utils/apiErrorMessage';
import { relocationOpennessLabel } from '../utils/relocationOpenness';
import { transportationAvailabilityLabel } from '../utils/transportationAvailability';

const LOOKUP = {
  residency: 'residency_type',
  marital: 'marital_status',
  passport: 'passport_validity',
  workplace: 'workplace_type',
  employment: 'employment_type',
  educationLevel: 'education_level',
  educationCompletion: 'education_completion',
} as const;

function PencilIcon() {
  return (
    <svg className="detail-card-edit-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden>
      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.829-2.828z" />
    </svg>
  );
}

function parseId(v: string): number | null {
  if (!v.trim()) return null;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? null : n;
}

function parseOptionalInt(v: string): number | null {
  if (!v.trim()) return null;
  const n = parseInt(v, 10);
  return Number.isNaN(n) ? null : n;
}

function parseOptionalFloat(v: string): number | null {
  if (!v.trim()) return null;
  const n = parseFloat(v);
  return Number.isNaN(n) ? null : n;
}

function SelectLookup({
  id,
  value,
  onChange,
  options,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  options: LookupOption[];
}) {
  return (
    <select id={id} className="detail-input" value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">—</option>
      {options.map((o) => (
        <option key={o.id} value={String(o.id)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

const TRANSPORT_OPTIONS: { value: TransportationAvailability | ''; label: string }[] = [
  { value: '', label: '—' },
  { value: 'yes', label: 'YES' },
  { value: 'no', label: 'NO' },
  { value: 'only_open_for_remote_opportunities', label: 'Only open for remote' },
];

const RELOCATION_OPTIONS: { value: RelocationOpenness | ''; label: string }[] = [
  { value: '', label: '—' },
  { value: 'yes', label: relocationOpennessLabel('yes') },
  { value: 'no', label: relocationOpennessLabel('no') },
  { value: 'for_missions_only', label: relocationOpennessLabel('for_missions_only') },
];

const BOOL_EMPTY = '';
const BOOL_OPTIONS: { value: string; label: string }[] = [
  { value: BOOL_EMPTY, label: '—' },
  { value: 'true', label: 'Yes' },
  { value: 'false', label: 'No' },
];

type PersonalDraft = {
  full_name: string;
  email: string;
  nationality: string;
  date_of_birth: string;
  current_address: string;
  residency_type_id: string;
  marital_status_id: string;
  number_of_dependents: string;
  religion_sect: string;
  passport_validity_status_id: string;
  has_transportation: TransportationAvailability | '';
};

type ProfessionalDraft = {
  applied_position: string;
  applied_position_location: string;
  years_of_experience: string;
  current_salary: string;
  expected_salary_remote: string;
  expected_salary_onsite: string;
  is_employed: string;
  employment_type_id: string;
  workplace_type_id: string;
  notice_period: string;
  is_open_for_relocation: RelocationOpenness | '';
  is_overtime_flexible: string;
  is_contract_flexible: string;
  education_level_id: string;
  education_completion_status_id: string;
  tech_stack: string;
};

function personalDraftFrom(c: Candidate): PersonalDraft {
  return {
    full_name: c.full_name ?? '',
    email: c.email ?? '',
    nationality: c.nationality ?? '',
    date_of_birth: c.date_of_birth ? c.date_of_birth.slice(0, 10) : '',
    current_address: c.current_address ?? '',
    residency_type_id: c.residency_type_id != null ? String(c.residency_type_id) : '',
    marital_status_id: c.marital_status_id != null ? String(c.marital_status_id) : '',
    number_of_dependents:
      c.number_of_dependents != null && c.number_of_dependents !== undefined
        ? String(c.number_of_dependents)
        : '',
    religion_sect: c.religion_sect ?? '',
    passport_validity_status_id:
      c.passport_validity_status_id != null ? String(c.passport_validity_status_id) : '',
    has_transportation: (c.has_transportation as TransportationAvailability | null) ?? '',
  };
}

function professionalDraftFrom(c: Candidate): ProfessionalDraft {
  return {
    applied_position: c.applied_position ?? '',
    applied_position_location: c.applied_position_location ?? '',
    years_of_experience:
      c.years_of_experience != null && c.years_of_experience !== undefined
        ? String(c.years_of_experience)
        : '',
    current_salary:
      c.current_salary != null && c.current_salary !== undefined ? String(c.current_salary) : '',
    expected_salary_remote:
      c.expected_salary_remote != null && c.expected_salary_remote !== undefined
        ? String(c.expected_salary_remote)
        : '',
    expected_salary_onsite:
      c.expected_salary_onsite != null && c.expected_salary_onsite !== undefined
        ? String(c.expected_salary_onsite)
        : '',
    is_employed:
      c.is_employed === true ? 'true' : c.is_employed === false ? 'false' : BOOL_EMPTY,
    employment_type_id: c.employment_type_id != null ? String(c.employment_type_id) : '',
    workplace_type_id: c.workplace_type_id != null ? String(c.workplace_type_id) : '',
    notice_period: c.notice_period ?? '',
    is_open_for_relocation: c.is_open_for_relocation ?? '',
    is_overtime_flexible:
      c.is_overtime_flexible === true ? 'true' : c.is_overtime_flexible === false ? 'false' : BOOL_EMPTY,
    is_contract_flexible:
      c.is_contract_flexible === true ? 'true' : c.is_contract_flexible === false ? 'false' : BOOL_EMPTY,
    education_level_id: c.education_level_id != null ? String(c.education_level_id) : '',
    education_completion_status_id:
      c.education_completion_status_id != null ? String(c.education_completion_status_id) : '',
    tech_stack: c.tech_stack?.length ? c.tech_stack.join(', ') : '',
  };
}

type CardProps = {
  candidate: Candidate;
  canWrite: boolean;
  lookups: Record<string, LookupOption[]>;
  onCandidateUpdated: (patch: CandidateProfilePatchResponse) => void;
  formatDate: (d: string | null) => string;
  displayName: (c: Candidate) => string;
};

export function PersonalInformationCard({
  candidate,
  canWrite,
  lookups,
  onCandidateUpdated,
  formatDate,
  displayName,
}: CardProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<PersonalDraft>(() => personalDraftFrom(candidate));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) setDraft(personalDraftFrom(candidate));
  }, [candidate, editing]);

  const cancel = () => {
    setDraft(personalDraftFrom(candidate));
    setEditing(false);
    setErr(null);
  };

  const save = async () => {
    setSaving(true);
    setErr(null);
    const payload: CandidateUpdatePayload = {
      full_name: draft.full_name.trim() || null,
      email: draft.email.trim() || null,
      date_of_birth: draft.date_of_birth.trim() || null,
      nationality: draft.nationality.trim() || null,
      current_address: draft.current_address.trim() || null,
      residency_type_id: parseId(draft.residency_type_id),
      marital_status_id: parseId(draft.marital_status_id),
      number_of_dependents: parseOptionalInt(draft.number_of_dependents),
      religion_sect: draft.religion_sect.trim() || null,
      passport_validity_status_id: parseId(draft.passport_validity_status_id),
      has_transportation: draft.has_transportation ? draft.has_transportation : null,
    };
    try {
      const patch = await patchCandidate(candidate.id, payload);
      onCandidateUpdated(patch);
      setEditing(false);
    } catch (e: unknown) {
      setErr(apiErrorMessage(e, 'Failed to save'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="detail-card detail-card-editable">
      <div className="detail-card-heading">
        <h2>Personal Information</h2>
        {canWrite && !editing && (
          <button
            type="button"
            className="detail-card-edit-btn"
            onClick={() => setEditing(true)}
            aria-label="Edit personal information"
          >
            <PencilIcon />
          </button>
        )}
      </div>
      {editing ? (
        <>
          <div className="detail-grid">
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-full-name">
                Full Name
              </label>
              <input
                id="cd-full-name"
                className="detail-input"
                value={draft.full_name}
                onChange={(e) => setDraft((d) => ({ ...d, full_name: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-email">
                Email
              </label>
              <input
                id="cd-email"
                type="email"
                className="detail-input"
                value={draft.email}
                onChange={(e) => setDraft((d) => ({ ...d, email: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-nationality">
                Nationality
              </label>
              <input
                id="cd-nationality"
                className="detail-input"
                value={draft.nationality}
                onChange={(e) => setDraft((d) => ({ ...d, nationality: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-dob">
                Date of Birth
              </label>
              <input
                id="cd-dob"
                type="date"
                className="detail-input"
                value={draft.date_of_birth}
                onChange={(e) => setDraft((d) => ({ ...d, date_of_birth: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit detail-item-wide">
              <label className="detail-label" htmlFor="cd-address">
                Current Address
              </label>
              <textarea
                id="cd-address"
                className="detail-input detail-textarea"
                rows={2}
                value={draft.current_address}
                onChange={(e) => setDraft((d) => ({ ...d, current_address: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-residency">
                Residency Type
              </label>
              <SelectLookup
                id="cd-residency"
                value={draft.residency_type_id}
                onChange={(v) => setDraft((d) => ({ ...d, residency_type_id: v }))}
                options={lookups[LOOKUP.residency] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-marital">
                Marital Status
              </label>
              <SelectLookup
                id="cd-marital"
                value={draft.marital_status_id}
                onChange={(v) => setDraft((d) => ({ ...d, marital_status_id: v }))}
                options={lookups[LOOKUP.marital] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-deps">
                Dependents
              </label>
              <input
                id="cd-deps"
                type="number"
                min={0}
                className="detail-input"
                value={draft.number_of_dependents}
                onChange={(e) => setDraft((d) => ({ ...d, number_of_dependents: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-transport">
                Transportation
              </label>
              <select
                id="cd-transport"
                className="detail-input"
                value={draft.has_transportation}
                onChange={(e) =>
                  setDraft((d) => ({
                    ...d,
                    has_transportation: e.target.value as TransportationAvailability | '',
                  }))
                }
              >
                {TRANSPORT_OPTIONS.map((o) => (
                  <option key={o.value || 'empty'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-passport">
                Passport Status
              </label>
              <SelectLookup
                id="cd-passport"
                value={draft.passport_validity_status_id}
                onChange={(v) => setDraft((d) => ({ ...d, passport_validity_status_id: v }))}
                options={lookups[LOOKUP.passport] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-religion">
                Religion / Sect
              </label>
              <input
                id="cd-religion"
                className="detail-input"
                value={draft.religion_sect}
                onChange={(e) => setDraft((d) => ({ ...d, religion_sect: e.target.value }))}
              />
            </div>
          </div>
          {err && (
            <p className="detail-edit-error" role="alert">
              {err}
            </p>
          )}
          <div className="detail-card-edit-actions">
            <button type="button" className="detail-edit-cancel-btn" disabled={saving} onClick={cancel}>
              Cancel
            </button>
            <button type="button" className="detail-edit-save-btn" disabled={saving} onClick={() => void save()}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </>
      ) : (
        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Full Name:</span>
            <span className="detail-value">{displayName(candidate)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Email:</span>
            <span className="detail-value">
              {candidate.email ? <a href={`mailto:${candidate.email}`}>{candidate.email}</a> : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Nationality:</span>
            <span className="detail-value">{candidate.nationality || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Date of Birth:</span>
            <span className="detail-value">{formatDate(candidate.date_of_birth)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Current Address:</span>
            <span className="detail-value">{candidate.current_address || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Residency Type:</span>
            <span className="detail-value">{candidate.residency_type_label || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Marital Status:</span>
            <span className="detail-value">{candidate.marital_status_label || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Dependents:</span>
            <span className="detail-value">
              {candidate.number_of_dependents !== null ? candidate.number_of_dependents : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Transportation:</span>
            <span className="detail-value">{transportationAvailabilityLabel(candidate.has_transportation)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Passport Status:</span>
            <span className="detail-value">{candidate.passport_validity_status_label || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Religion / Sect:</span>
            <span className="detail-value">{candidate.religion_sect || '-'}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export function ProfessionalInformationCard({
  candidate,
  canWrite,
  lookups,
  onCandidateUpdated,
  formatDate: _formatDate,
  displayName: _displayName,
}: CardProps) {
  void _formatDate;
  void _displayName;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<ProfessionalDraft>(() => professionalDraftFrom(candidate));
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) setDraft(professionalDraftFrom(candidate));
  }, [candidate, editing]);

  const cancel = () => {
    setDraft(professionalDraftFrom(candidate));
    setEditing(false);
    setErr(null);
  };

  const save = async () => {
    setSaving(true);
    setErr(null);
    const techParts = draft.tech_stack
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const payload: CandidateUpdatePayload = {
      applied_position: draft.applied_position.trim() || null,
      applied_position_location: draft.applied_position_location.trim() || null,
      years_of_experience: parseOptionalFloat(draft.years_of_experience),
      current_salary: parseOptionalFloat(draft.current_salary),
      expected_salary_remote: parseOptionalFloat(draft.expected_salary_remote),
      expected_salary_onsite: parseOptionalFloat(draft.expected_salary_onsite),
      is_employed:
        draft.is_employed === BOOL_EMPTY ? null : draft.is_employed === 'true',
      employment_type_id: parseId(draft.employment_type_id),
      workplace_type_id: parseId(draft.workplace_type_id),
      notice_period: draft.notice_period.trim() || null,
      is_open_for_relocation: draft.is_open_for_relocation ? draft.is_open_for_relocation : null,
      is_overtime_flexible:
        draft.is_overtime_flexible === BOOL_EMPTY ? null : draft.is_overtime_flexible === 'true',
      is_contract_flexible:
        draft.is_contract_flexible === BOOL_EMPTY ? null : draft.is_contract_flexible === 'true',
      education_level_id: parseId(draft.education_level_id),
      education_completion_status_id: parseId(draft.education_completion_status_id),
      tech_stack: techParts,
    };
    try {
      const patch = await patchCandidate(candidate.id, payload);
      onCandidateUpdated(patch);
      setEditing(false);
    } catch (e: unknown) {
      setErr(apiErrorMessage(e, 'Failed to save'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="detail-card detail-card-editable">
      <div className="detail-card-heading">
        <h2>Professional Information</h2>
        {canWrite && !editing && (
          <button
            type="button"
            className="detail-card-edit-btn"
            onClick={() => setEditing(true)}
            aria-label="Edit professional information"
          >
            <PencilIcon />
          </button>
        )}
      </div>
      {editing ? (
        <>
          <div className="detail-grid">
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-pos">
                Applied Position
              </label>
              <input
                id="cd-pos"
                className="detail-input"
                value={draft.applied_position}
                onChange={(e) => setDraft((d) => ({ ...d, applied_position: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-loc">
                Location
              </label>
              <input
                id="cd-loc"
                className="detail-input"
                value={draft.applied_position_location}
                onChange={(e) => setDraft((d) => ({ ...d, applied_position_location: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-yoe">
                Years of Experience
              </label>
              <input
                id="cd-yoe"
                type="number"
                min={0}
                step={0.1}
                className="detail-input"
                value={draft.years_of_experience}
                onChange={(e) => setDraft((d) => ({ ...d, years_of_experience: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-csal">
                Current Salary
              </label>
              <input
                id="cd-csal"
                type="number"
                min={0}
                step={0.01}
                className="detail-input"
                value={draft.current_salary}
                onChange={(e) => setDraft((d) => ({ ...d, current_salary: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-esr">
                Expected Salary (Remote)
              </label>
              <input
                id="cd-esr"
                type="number"
                min={0}
                step={0.01}
                className="detail-input"
                value={draft.expected_salary_remote}
                onChange={(e) => setDraft((d) => ({ ...d, expected_salary_remote: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-eso">
                Expected Salary (Onsite)
              </label>
              <input
                id="cd-eso"
                type="number"
                min={0}
                step={0.01}
                className="detail-input"
                value={draft.expected_salary_onsite}
                onChange={(e) => setDraft((d) => ({ ...d, expected_salary_onsite: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-emp">
                Is Employed
              </label>
              <select
                id="cd-emp"
                className="detail-input"
                value={draft.is_employed}
                onChange={(e) => setDraft((d) => ({ ...d, is_employed: e.target.value }))}
              >
                {BOOL_OPTIONS.map((o) => (
                  <option key={o.value || 'e'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-emptype">
                Employment Type
              </label>
              <SelectLookup
                id="cd-emptype"
                value={draft.employment_type_id}
                onChange={(v) => setDraft((d) => ({ ...d, employment_type_id: v }))}
                options={lookups[LOOKUP.employment] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-wptype">
                Workplace Type
              </label>
              <SelectLookup
                id="cd-wptype"
                value={draft.workplace_type_id}
                onChange={(v) => setDraft((d) => ({ ...d, workplace_type_id: v }))}
                options={lookups[LOOKUP.workplace] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-notice">
                Notice Period
              </label>
              <input
                id="cd-notice"
                className="detail-input"
                value={draft.notice_period}
                onChange={(e) => setDraft((d) => ({ ...d, notice_period: e.target.value }))}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-reloc">
                Open for Relocation
              </label>
              <select
                id="cd-reloc"
                className="detail-input"
                value={draft.is_open_for_relocation}
                onChange={(e) =>
                  setDraft((d) => ({
                    ...d,
                    is_open_for_relocation: e.target.value as RelocationOpenness | '',
                  }))
                }
              >
                {RELOCATION_OPTIONS.map((o) => (
                  <option key={o.value || 'rel-e'} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-ot">
                Overtime Flexible
              </label>
              <select
                id="cd-ot"
                className="detail-input"
                value={draft.is_overtime_flexible}
                onChange={(e) => setDraft((d) => ({ ...d, is_overtime_flexible: e.target.value }))}
              >
                {BOOL_OPTIONS.map((o) => (
                  <option key={`ot-${o.value}`} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-contract">
                Contract Flexible
              </label>
              <select
                id="cd-contract"
                className="detail-input"
                value={draft.is_contract_flexible}
                onChange={(e) => setDraft((d) => ({ ...d, is_contract_flexible: e.target.value }))}
              >
                {BOOL_OPTIONS.map((o) => (
                  <option key={`cf-${o.value}`} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-edu">
                Education Level
              </label>
              <SelectLookup
                id="cd-edu"
                value={draft.education_level_id}
                onChange={(v) => setDraft((d) => ({ ...d, education_level_id: v }))}
                options={lookups[LOOKUP.educationLevel] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit">
              <label className="detail-label" htmlFor="cd-edust">
                Education Status
              </label>
              <SelectLookup
                id="cd-edust"
                value={draft.education_completion_status_id}
                onChange={(v) => setDraft((d) => ({ ...d, education_completion_status_id: v }))}
                options={lookups[LOOKUP.educationCompletion] ?? []}
              />
            </div>
            <div className="detail-item detail-item-edit detail-item-wide">
              <label className="detail-label" htmlFor="cd-tech">
                Tech stack (comma-separated)
              </label>
              <input
                id="cd-tech"
                className="detail-input"
                value={draft.tech_stack}
                onChange={(e) => setDraft((d) => ({ ...d, tech_stack: e.target.value }))}
              />
            </div>
          </div>
          {err && (
            <p className="detail-edit-error" role="alert">
              {err}
            </p>
          )}
          <div className="detail-card-edit-actions">
            <button type="button" className="detail-edit-cancel-btn" disabled={saving} onClick={cancel}>
              Cancel
            </button>
            <button type="button" className="detail-edit-save-btn" disabled={saving} onClick={() => void save()}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </>
      ) : (
        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Applied Position:</span>
            <span className="detail-value">{candidate.applied_position || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Location:</span>
            <span className="detail-value">{candidate.applied_position_location || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Years of Experience:</span>
            <span className="detail-value">
              {candidate.years_of_experience !== null && candidate.years_of_experience !== undefined
                ? `${candidate.years_of_experience} years`
                : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Current Salary:</span>
            <span className="detail-value">
              {candidate.current_salary !== null && candidate.current_salary !== undefined
                ? `$${Number(candidate.current_salary).toLocaleString()}`
                : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Expected Salary (Remote):</span>
            <span className="detail-value">
              {candidate.expected_salary_remote !== null && candidate.expected_salary_remote !== undefined
                ? `$${Number(candidate.expected_salary_remote).toLocaleString()}`
                : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Expected Salary (Onsite):</span>
            <span className="detail-value">
              {candidate.expected_salary_onsite !== null && candidate.expected_salary_onsite !== undefined
                ? `$${Number(candidate.expected_salary_onsite).toLocaleString()}`
                : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Is Employed:</span>
            <span className="detail-value">
              {candidate.is_employed === true ? 'Yes' : candidate.is_employed === false ? 'No' : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Employment Type:</span>
            <span className="detail-value">{candidate.employment_type_label || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Workplace Type:</span>
            <span className="detail-value">{candidate.workplace_type_label || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Notice Period:</span>
            <span className="detail-value">{candidate.notice_period || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Open for Relocation:</span>
            <span className="detail-value">{relocationOpennessLabel(candidate.is_open_for_relocation)}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Overtime Flexible:</span>
            <span className="detail-value">
              {candidate.is_overtime_flexible === true ? 'Yes' : candidate.is_overtime_flexible === false ? 'No' : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Contract Flexible:</span>
            <span className="detail-value">
              {candidate.is_contract_flexible === true ? 'Yes' : candidate.is_contract_flexible === false ? 'No' : '-'}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Education Level:</span>
            <span className="detail-value">{candidate.education_level_label || '-'}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Education Status:</span>
            <span className="detail-value">{candidate.education_completion_status_label || '-'}</span>
          </div>
          <div className="detail-item detail-item-wide">
            <span className="detail-label">Tech Stack:</span>
            <span className="detail-value">
              {candidate.tech_stack && candidate.tech_stack.length > 0
                ? candidate.tech_stack.join(', ')
                : '-'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
