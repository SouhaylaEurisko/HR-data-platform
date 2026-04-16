import { useEffect, useState } from 'react';
import type { Candidate, RelocationOpenness, TransportationAvailability } from '../types/api';
import {
  patchCandidatePersonal,
  patchCandidateProfessional,
  type CandidatePersonalPatchBody,
  type CandidateProfessionalPatchBody,
} from '../api/candidates';
import { getLookupOptions, type LookupOptionRow } from '../api/lookups';
import { apiErrorMessage } from '../utils/apiErrorMessage';
import './CandidateSectionEditDialog.css';

export type CandidateEditSection = 'personal' | 'professional';

type Props = {
  open: boolean;
  section: CandidateEditSection;
  candidate: Candidate;
  onClose: () => void;
  onSaved: (updated: Candidate) => void;
};

function dateInputValue(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = iso.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(d) ? d : '';
}

function parseOptionalInt(s: string): number | null {
  const t = s.trim();
  if (!t) return null;
  const n = parseInt(t, 10);
  return Number.isFinite(n) ? n : null;
}

function parseOptionalNumber(s: string): number | null {
  const t = s.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function triBoolString(v: boolean | null | undefined): '' | 'true' | 'false' {
  if (v === true) return 'true';
  if (v === false) return 'false';
  return '';
}

function LookupSelect({
  value,
  onChange,
  options,
  id,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  options: LookupOptionRow[];
}) {
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
      <option value="">—</option>
      {options.map((o) => (
        <option key={o.id} value={String(o.id)}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

export default function CandidateSectionEditDialog({
  open,
  section,
  candidate,
  onClose,
  onSaved,
}: Props) {
  const [lookupsLoading, setLookupsLoading] = useState(false);
  const [residencyOpts, setResidencyOpts] = useState<LookupOptionRow[]>([]);
  const [maritalOpts, setMaritalOpts] = useState<LookupOptionRow[]>([]);
  const [passportOpts, setPassportOpts] = useState<LookupOptionRow[]>([]);
  const [workplaceOpts, setWorkplaceOpts] = useState<LookupOptionRow[]>([]);
  const [employmentOpts, setEmploymentOpts] = useState<LookupOptionRow[]>([]);
  const [eduLevelOpts, setEduLevelOpts] = useState<LookupOptionRow[]>([]);
  const [eduCompleteOpts, setEduCompleteOpts] = useState<LookupOptionRow[]>([]);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [dateOfBirth, setDateOfBirth] = useState('');
  const [nationality, setNationality] = useState('');
  const [currentAddress, setCurrentAddress] = useState('');
  const [residencyTypeId, setResidencyTypeId] = useState('');
  const [maritalStatusId, setMaritalStatusId] = useState('');
  const [dependents, setDependents] = useState('');
  const [religionSect, setReligionSect] = useState('');
  const [passportId, setPassportId] = useState('');
  const [transportation, setTransportation] = useState<'' | TransportationAvailability>('');

  const [appliedPosition, setAppliedPosition] = useState('');
  const [appliedLocation, setAppliedLocation] = useState('');
  const [relocation, setRelocation] = useState<'' | RelocationOpenness>('');
  const [yearsExp, setYearsExp] = useState('');
  const [employed, setEmployed] = useState<'' | 'true' | 'false'>('');
  const [currentSalary, setCurrentSalary] = useState('');
  const [expectedRemote, setExpectedRemote] = useState('');
  const [expectedOnsite, setExpectedOnsite] = useState('');
  const [noticePeriod, setNoticePeriod] = useState('');
  const [overtimeFlex, setOvertimeFlex] = useState<'' | 'true' | 'false'>('');
  const [contractFlex, setContractFlex] = useState<'' | 'true' | 'false'>('');
  const [workplaceTypeId, setWorkplaceTypeId] = useState('');
  const [employmentTypeId, setEmploymentTypeId] = useState('');
  const [educationLevelId, setEducationLevelId] = useState('');
  const [educationCompleteId, setEducationCompleteId] = useState('');
  const [techStack, setTechStack] = useState('');

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
  }, [open, section]);

  useEffect(() => {
    if (!open || !candidate) return;

    setFullName(candidate.full_name ?? '');
    setEmail(candidate.email ?? '');
    setDateOfBirth(dateInputValue(candidate.date_of_birth));
    setNationality(candidate.nationality ?? '');
    setCurrentAddress(candidate.current_address ?? '');
    setResidencyTypeId(candidate.residency_type_id != null ? String(candidate.residency_type_id) : '');
    setMaritalStatusId(candidate.marital_status_id != null ? String(candidate.marital_status_id) : '');
    setDependents(
      candidate.number_of_dependents != null && candidate.number_of_dependents !== undefined
        ? String(candidate.number_of_dependents)
        : ''
    );
    setReligionSect(candidate.religion_sect ?? '');
    setPassportId(
      candidate.passport_validity_status_id != null ? String(candidate.passport_validity_status_id) : ''
    );
    setTransportation((candidate.has_transportation ?? '') as '' | TransportationAvailability);

    setAppliedPosition(candidate.applied_position ?? '');
    setAppliedLocation(candidate.applied_position_location ?? '');
    setRelocation((candidate.is_open_for_relocation ?? '') as '' | RelocationOpenness);
    setYearsExp(
      candidate.years_of_experience != null && candidate.years_of_experience !== undefined
        ? String(candidate.years_of_experience)
        : ''
    );
    setEmployed(triBoolString(candidate.is_employed));
    setCurrentSalary(
      candidate.current_salary != null && candidate.current_salary !== undefined
        ? String(candidate.current_salary)
        : ''
    );
    setExpectedRemote(
      candidate.expected_salary_remote != null && candidate.expected_salary_remote !== undefined
        ? String(candidate.expected_salary_remote)
        : ''
    );
    setExpectedOnsite(
      candidate.expected_salary_onsite != null && candidate.expected_salary_onsite !== undefined
        ? String(candidate.expected_salary_onsite)
        : ''
    );
    setNoticePeriod(candidate.notice_period ?? '');
    setOvertimeFlex(triBoolString(candidate.is_overtime_flexible));
    setContractFlex(triBoolString(candidate.is_contract_flexible));
    setWorkplaceTypeId(candidate.workplace_type_id != null ? String(candidate.workplace_type_id) : '');
    setEmploymentTypeId(candidate.employment_type_id != null ? String(candidate.employment_type_id) : '');
    setEducationLevelId(candidate.education_level_id != null ? String(candidate.education_level_id) : '');
    setEducationCompleteId(
      candidate.education_completion_status_id != null
        ? String(candidate.education_completion_status_id)
        : ''
    );
    setTechStack((candidate.tech_stack ?? []).join(', '));
  }, [open, candidate, section]);

  useEffect(() => {
    if (!open || !candidate) return;
    let cancelled = false;
    const org = candidate.organization_id;

    async function load() {
      setLookupsLoading(true);
      try {
        if (section === 'personal') {
          const [r, m, p] = await Promise.all([
            getLookupOptions('residency_type', org),
            getLookupOptions('marital_status', org),
            getLookupOptions('passport_validity', org),
          ]);
          if (!cancelled) {
            setResidencyOpts(r);
            setMaritalOpts(m);
            setPassportOpts(p);
          }
        } else {
          const [w, e, el, ec] = await Promise.all([
            getLookupOptions('workplace_type', org),
            getLookupOptions('employment_type', org),
            getLookupOptions('education_level', org),
            getLookupOptions('education_completion', org),
          ]);
          if (!cancelled) {
            setWorkplaceOpts(w);
            setEmploymentOpts(e);
            setEduLevelOpts(el);
            setEduCompleteOpts(ec);
          }
        }
      } catch {
        if (!cancelled) {
          setError('Failed to load dropdown options. Try again or refresh the page.');
        }
      } finally {
        if (!cancelled) setLookupsLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [open, candidate, section]);

  const handleSave = async () => {
    setError(null);
    setSaving(true);
    try {
      if (section === 'personal') {
        const deps = parseOptionalInt(dependents);
        if (dependents.trim() !== '' && deps === null) {
          setError('Dependents must be a whole number.');
          return;
        }
        const body: CandidatePersonalPatchBody = {
          full_name: fullName.trim() || null,
          email: email.trim() || null,
          date_of_birth: dateOfBirth || null,
          nationality: nationality.trim() || null,
          current_address: currentAddress.trim() || null,
          residency_type_id: residencyTypeId ? parseInt(residencyTypeId, 10) : null,
          marital_status_id: maritalStatusId ? parseInt(maritalStatusId, 10) : null,
          number_of_dependents: deps,
          religion_sect: religionSect.trim() || null,
          passport_validity_status_id: passportId ? parseInt(passportId, 10) : null,
          has_transportation: transportation === '' ? null : transportation,
        };
        const updated = await patchCandidatePersonal(candidate.id, body, candidate.organization_id);
        onSaved(updated);
      } else {
        const y = parseOptionalNumber(yearsExp);
        if (yearsExp.trim() !== '' && y === null) {
          setError('Years of experience must be a number.');
          return;
        }
        const cs = parseOptionalNumber(currentSalary);
        if (currentSalary.trim() !== '' && cs === null) {
          setError('Current salary must be a number.');
          return;
        }
        const er = parseOptionalNumber(expectedRemote);
        if (expectedRemote.trim() !== '' && er === null) {
          setError('Expected remote salary must be a number.');
          return;
        }
        const eo = parseOptionalNumber(expectedOnsite);
        if (expectedOnsite.trim() !== '' && eo === null) {
          setError('Expected onsite salary must be a number.');
          return;
        }
        const stack = techStack
          .split(/[,;\n]+/)
          .map((s) => s.trim())
          .filter(Boolean);
        const body: CandidateProfessionalPatchBody = {
          applied_position: appliedPosition.trim() || null,
          applied_position_location: appliedLocation.trim() || null,
          is_open_for_relocation: relocation === '' ? null : relocation,
          years_of_experience: y,
          is_employed: employed === '' ? null : employed === 'true',
          current_salary: cs,
          expected_salary_remote: er,
          expected_salary_onsite: eo,
          notice_period: noticePeriod.trim() || null,
          is_overtime_flexible: overtimeFlex === '' ? null : overtimeFlex === 'true',
          is_contract_flexible: contractFlex === '' ? null : contractFlex === 'true',
          workplace_type_id: workplaceTypeId ? parseInt(workplaceTypeId, 10) : null,
          employment_type_id: employmentTypeId ? parseInt(employmentTypeId, 10) : null,
          tech_stack: stack,
          education_level_id: educationLevelId ? parseInt(educationLevelId, 10) : null,
          education_completion_status_id: educationCompleteId ? parseInt(educationCompleteId, 10) : null,
        };
        const updated = await patchCandidateProfessional(
          candidate.id,
          body,
          candidate.organization_id
        );
        onSaved(updated);
      }
      onClose();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'Could not save changes'));
    } finally {
      setSaving(false);
    }
  };

  if (!open) return null;

  const title = section === 'personal' ? 'Edit personal information' : 'Edit professional information';

  return (
    <div className="cand-edit-overlay" onClick={onClose}>
      <div className="cand-edit-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="cand-edit-dialog-header">
          <h3 id="cand-edit-title">{title}</h3>
          <button type="button" className="cand-edit-close" aria-label="Close" onClick={onClose}>
            ×
          </button>
        </div>
        <div className="cand-edit-body" aria-labelledby="cand-edit-title">
          {lookupsLoading && <p className="cand-edit-loading">Loading options…</p>}
          {error && (
            <p className="cand-edit-error" role="alert">
              {error}
            </p>
          )}

          {section === 'personal' ? (
            <div className="cand-edit-fields">
              <div className="cand-edit-field">
                <label htmlFor="ce-full-name">Full name</label>
                <input id="ce-full-name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-email">Email</label>
                <input
                  id="ce-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-dob">Date of birth</label>
                <input
                  id="ce-dob"
                  type="date"
                  value={dateOfBirth}
                  onChange={(e) => setDateOfBirth(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-nationality">Nationality</label>
                <input id="ce-nationality" value={nationality} onChange={(e) => setNationality(e.target.value)} />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-address">Current address</label>
                <textarea
                  id="ce-address"
                  value={currentAddress}
                  onChange={(e) => setCurrentAddress(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-residency">Residency type</label>
                <LookupSelect
                  id="ce-residency"
                  value={residencyTypeId}
                  onChange={setResidencyTypeId}
                  options={residencyOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-marital">Marital status</label>
                <LookupSelect
                  id="ce-marital"
                  value={maritalStatusId}
                  onChange={setMaritalStatusId}
                  options={maritalOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-deps">Number of dependents</label>
                <input
                  id="ce-deps"
                  inputMode="numeric"
                  value={dependents}
                  onChange={(e) => setDependents(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-religion">Religion / sect</label>
                <input id="ce-religion" value={religionSect} onChange={(e) => setReligionSect(e.target.value)} />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-passport">Passport validity</label>
                <LookupSelect
                  id="ce-passport"
                  value={passportId}
                  onChange={setPassportId}
                  options={passportOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-transport">Transportation</label>
                <select
                  id="ce-transport"
                  value={transportation}
                  onChange={(e) =>
                    setTransportation(e.target.value as '' | TransportationAvailability)
                  }
                >
                  <option value="">—</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="only_open_for_remote_opportunities">Only open for remote</option>
                </select>
              </div>
            </div>
          ) : (
            <div className="cand-edit-fields">
              <div className="cand-edit-field">
                <label htmlFor="ce-position">Applied position</label>
                <input
                  id="ce-position"
                  value={appliedPosition}
                  onChange={(e) => setAppliedPosition(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-loc">Location</label>
                <input id="ce-loc" value={appliedLocation} onChange={(e) => setAppliedLocation(e.target.value)} />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-reloc">Open for relocation</label>
                <select
                  id="ce-reloc"
                  value={relocation}
                  onChange={(e) => setRelocation(e.target.value as '' | RelocationOpenness)}
                >
                  <option value="">—</option>
                  <option value="yes">Yes</option>
                  <option value="no">No</option>
                  <option value="for_missions_only">For missions only</option>
                </select>
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-years">Years of experience</label>
                <input
                  id="ce-years"
                  inputMode="decimal"
                  value={yearsExp}
                  onChange={(e) => setYearsExp(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-employed">Currently employed</label>
                <select
                  id="ce-employed"
                  value={employed}
                  onChange={(e) => setEmployed(e.target.value as '' | 'true' | 'false')}
                >
                  <option value="">—</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-cur-sal">Current salary (USD)</label>
                <input
                  id="ce-cur-sal"
                  inputMode="decimal"
                  value={currentSalary}
                  onChange={(e) => setCurrentSalary(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-er">Expected salary remote (USD)</label>
                <input
                  id="ce-er"
                  inputMode="decimal"
                  value={expectedRemote}
                  onChange={(e) => setExpectedRemote(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-eo">Expected salary onsite (USD)</label>
                <input
                  id="ce-eo"
                  inputMode="decimal"
                  value={expectedOnsite}
                  onChange={(e) => setExpectedOnsite(e.target.value)}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-notice">Notice period</label>
                <input id="ce-notice" value={noticePeriod} onChange={(e) => setNoticePeriod(e.target.value)} />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-ot">Overtime flexible</label>
                <select
                  id="ce-ot"
                  value={overtimeFlex}
                  onChange={(e) => setOvertimeFlex(e.target.value as '' | 'true' | 'false')}
                >
                  <option value="">—</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-ct">Contract flexible</label>
                <select
                  id="ce-ct"
                  value={contractFlex}
                  onChange={(e) => setContractFlex(e.target.value as '' | 'true' | 'false')}
                >
                  <option value="">—</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-wp">Workplace type</label>
                <LookupSelect
                  id="ce-wp"
                  value={workplaceTypeId}
                  onChange={setWorkplaceTypeId}
                  options={workplaceOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-et">Employment type</label>
                <LookupSelect
                  id="ce-et"
                  value={employmentTypeId}
                  onChange={setEmploymentTypeId}
                  options={employmentOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-edu">Education level</label>
                <LookupSelect
                  id="ce-edu"
                  value={educationLevelId}
                  onChange={setEducationLevelId}
                  options={eduLevelOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-edu-st">Education completion</label>
                <LookupSelect
                  id="ce-edu-st"
                  value={educationCompleteId}
                  onChange={setEducationCompleteId}
                  options={eduCompleteOpts}
                />
              </div>
              <div className="cand-edit-field">
                <label htmlFor="ce-tech">Tech stack (comma-separated)</label>
                <textarea id="ce-tech" value={techStack} onChange={(e) => setTechStack(e.target.value)} />
              </div>
            </div>
          )}

          <div className="cand-edit-actions">
            <button type="button" className="cand-edit-cancel" onClick={onClose} disabled={saving}>
              Cancel
            </button>
            <button
              type="button"
              className="cand-edit-save"
              onClick={() => void handleSave()}
              disabled={saving || lookupsLoading}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
