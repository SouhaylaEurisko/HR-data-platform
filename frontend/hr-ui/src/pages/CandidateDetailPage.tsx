import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import ApplicationStatusBadge from '../components/ApplicationStatusBadge';
import { getCandidateById, patchCandidateApplicationStatus, postCandidateHrStageComment } from '../api/candidates';
import { APPLICATION_STATUS_OPTIONS, parseApplicationStatus } from '../constants/applicationStatus';
import {
  HR_STAGE_DEFS,
  latestStageComment,
  type HrStageDef,
  type HrStageKey,
} from '../constants/hrStages.ts';
import type { ApplicationStatus, Candidate, HrStageCommentEntry } from '../types/api';
import { apiErrorMessage } from '../utils/apiErrorMessage';
import { relocationOpennessLabel } from '../utils/relocationOpenness';
import './CandidateDetailPage.css';

function entriesForStage(c: Candidate, key: HrStageKey): HrStageCommentEntry[] {
  const s = c.hr_stage_comments?.[key];
  return Array.isArray(s) ? s : [];
}

type CandidateDetailLocationState = {
  fromChat?: boolean;
  focusHrComment?: boolean;
};

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const fromChat =
    (location.state as CandidateDetailLocationState | null)?.fromChat ?? false;

  const goBack = () => {
    if (fromChat) {
      navigate('/chat');
    } else {
      navigate(-1);
    }
  };

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCustomFields, setShowCustomFields] = useState(false);
  const [newCommentText, setNewCommentText] = useState('');
  const [selectedHrStage, setSelectedHrStage] = useState<HrStageKey>('pre_screening');
  const [hrStageMenuOpen, setHrStageMenuOpen] = useState(false);
  const [hrHistoryOpen, setHrHistoryOpen] = useState(false);
  const [commentSaving, setCommentSaving] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);
  const [statusSaving, setStatusSaving] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const didScrollToHrComment = useRef(false);
  const hrStageSelectRef = useRef<HTMLDivElement>(null);
  const hrLatestBlockRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    didScrollToHrComment.current = false;
    setSelectedHrStage('pre_screening');
    setHrStageMenuOpen(false);
    setHrHistoryOpen(false);
    setNewCommentText('');
  }, [id]);

  useEffect(() => {
    if (!hrStageMenuOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      const el = hrStageSelectRef.current;
      if (el && !el.contains(e.target as Node)) setHrStageMenuOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [hrStageMenuOpen]);

  useEffect(() => {
    if (!hrHistoryOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      const el = hrLatestBlockRef.current;
      if (el && !el.contains(e.target as Node)) setHrHistoryOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  }, [hrHistoryOpen]);

  const stageHasLatestComment =
    !!candidate && !!latestStageComment(entriesForStage(candidate, selectedHrStage));

  useEffect(() => {
    if (!stageHasLatestComment) setHrHistoryOpen(false);
  }, [stageHasLatestComment, selectedHrStage]);

  useEffect(() => {
    const fetchCandidate = async () => {
      if (!id) {
        setError('Invalid candidate ID');
        setLoading(false);
        return;
      }

      try {
        const candidateId = parseInt(id, 10);
        if (isNaN(candidateId)) {
          setError('Invalid candidate ID');
          setLoading(false);
          return;
        }
        const data = await getCandidateById(candidateId);
        setCandidate(data);
      } catch (err: unknown) {
        setError(apiErrorMessage(err, 'Failed to load candidate details'));
      } finally {
        setLoading(false);
      }
    };
    fetchCandidate();
  }, [id]);

  useEffect(() => {
    if (!candidate || didScrollToHrComment.current) return;
    const st = location.state as CandidateDetailLocationState | null | undefined;
    if (!st?.focusHrComment) return;
    didScrollToHrComment.current = true;
    const run = () => {
      document.getElementById('hr-comment-section')?.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
      document.getElementById('hr-stage-select-trigger')?.focus();
    };
    requestAnimationFrame(() => setTimeout(run, 50));
    navigate(location.pathname, {
      replace: true,
      state: { fromChat: st.fromChat },
    });
  }, [candidate, location.pathname, location.state, navigate]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  const displayName = (c: Candidate) => c.full_name || '-';

  if (loading) {
    return (
      <div className="candidate-detail-page">
        <div className="loading">Loading candidate details...</div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="candidate-detail-page">
        <div className="error-message" role="alert">
          {error || 'Candidate not found'}
        </div>
        <button onClick={goBack} className="back-button">
          &larr; {fromChat ? 'Back to Chat' : 'Back to Candidates'}
        </button>
      </div>
    );
  }

  const hasCustomFields = candidate.custom_fields && Object.keys(candidate.custom_fields).length > 0;

  const handleAddHrStageComment = async () => {
    if (!candidate) return;
    const text = newCommentText.trim();
    if (!text) return;
    setCommentSaving(true);
    setCommentError(null);
    try {
      const updated = await postCandidateHrStageComment(candidate.id, {
        stage: selectedHrStage,
        text,
      });
      setCandidate(updated);
      setNewCommentText('');
    } catch (err: unknown) {
      setCommentError(apiErrorMessage(err, 'Failed to add comment'));
    } finally {
      setCommentSaving(false);
    }
  };

  const handleApplicationStatusChange = async (value: ApplicationStatus) => {
    if (!candidate) return;
    const current = parseApplicationStatus(candidate.application_status);
    if (current === value) return;
    setStatusSaving(true);
    setStatusError(null);
    const prev = candidate.application_status;
    setCandidate({ ...candidate, application_status: value });
    try {
      const updated = await patchCandidateApplicationStatus(candidate.id, value);
      setCandidate(updated);
    } catch (err: unknown) {
      setCandidate({ ...candidate, application_status: prev });
      setStatusError(apiErrorMessage(err, 'Failed to save status'));
    } finally {
      setStatusSaving(false);
    }
  };

  const headerApplicationStatus = parseApplicationStatus(candidate.application_status);
  const selectedEntries = entriesForStage(candidate, selectedHrStage);
  const selectedLatest = latestStageComment(selectedEntries);
  const selectedEarlier =
    selectedEntries.length > 1
      ? selectedEntries.slice(0, -1).reverse()
      : [];
  const selectedStageLabel =
    (HR_STAGE_DEFS as readonly HrStageDef[]).find((def: HrStageDef) => def.key === selectedHrStage)
      ?.label ?? 'this stage';

  return (
    <div className="candidate-detail-page">
      <div className="detail-header">
        <button onClick={goBack} className="back-button">
          &larr; {fromChat ? 'Back to Chat' : 'Back to Candidates'}
        </button>
        <div className="detail-header-title-row">
          <h1>{displayName(candidate)}</h1>
          <ApplicationStatusBadge status={headerApplicationStatus} size="large" />
        </div>
        {candidate.application_index != null &&
          candidate.application_total != null &&
          candidate.application_total >= 1 && (
            <div className="application-context-banner" role="region" aria-label="Application context">
              <p className="application-context-main">
                <span className="application-context-badge">
                  Application {candidate.application_index} of {candidate.application_total}
                </span>
                {candidate.applied_position ? (
                  <span className="application-context-position">
                    {' '}
                    — Role: <strong>{candidate.applied_position}</strong>
                  </span>
                ) : null}
              </p>
              {candidate.related_applications &&
                candidate.related_applications.filter((r) => r.id !== candidate.id).length > 0 && (
                  <div className="application-context-siblings">
                    <span className="application-context-siblings-label">Other applications:</span>
                    <ul>
                      {candidate.related_applications
                        .filter((r) => r.id !== candidate.id)
                        .map((r) => (
                          <li key={r.id}>
                            <button
                              type="button"
                              className="application-context-link"
                              onClick={() => navigate(`/candidates/${r.id}`)}
                            >
                              {r.applied_position || 'Unknown role'}
                              {r.applied_at
                                ? ` (${new Date(r.applied_at).toLocaleDateString()})`
                                : ''}
                            </button>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
            </div>
          )}
      </div>

      <div className="detail-content">
        {/* Personal Information */}
        <div className="detail-card">
          <h2>Personal Information</h2>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Full Name:</span>
              <span className="detail-value">{displayName(candidate)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Email:</span>
              <span className="detail-value">
                {candidate.email ? (
                  <a href={`mailto:${candidate.email}`}>{candidate.email}</a>
                ) : '-'}
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
              <span className="detail-value">
                {candidate.has_transportation === true ? 'Yes' : candidate.has_transportation === false ? 'No' : '-'}
              </span>
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
        </div>

        {/* Professional Information */}
        <div className="detail-card">
          <h2>Professional Information</h2>
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
              <span className="detail-value">
                {relocationOpennessLabel(candidate.is_open_for_relocation)}
              </span>
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
            {candidate.tech_stack && candidate.tech_stack.length > 0 && (
              <div className="detail-item detail-item-wide">
                <span className="detail-label">Tech Stack:</span>
                <span className="detail-value">{candidate.tech_stack.join(', ')}</span>
              </div>
            )}
          </div>
        </div>

        {/* Custom Fields */}
        {hasCustomFields && (
          <div className="detail-card detail-card-custom-fields">
            <div className="custom-fields-header">
              <h2>Custom Fields</h2>
              <button
                onClick={() => setShowCustomFields(!showCustomFields)}
                className="toggle-raw-data-btn"
              >
                {showCustomFields ? 'Hide' : 'Show'} Details
              </button>
            </div>
            {showCustomFields && (
              <div className="custom-fields-list">
                {Object.entries(candidate.custom_fields).map(([key, value]) => (
                  <div className="custom-field-row" key={key}>
                    <span className="custom-field-label">
                      {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <span className="custom-field-value">
                      {value === null || value === undefined || value === '' ? '-' : String(value)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* HR comments: one stage at a time via dropdown + single textarea */}
        <div
          className="detail-card detail-card-hr-comment"
          id="hr-comment-section"
        >
          <div className="custom-fields-header">
            <h2>HR comments</h2>
          </div>
          <p className="hr-comment-hint">
            Add a comment and track your comment history for each stage.
          </p>
          <div className="hr-stage-and-status-row">
            <div className="hr-stage-selector-group">
              <label className="hr-stage-select-label" id="hr-stage-select-label" htmlFor="hr-stage-select-trigger">
                Stage
              </label>
              <div className="hr-stage-select-wrapper" ref={hrStageSelectRef}>
                <button
                  type="button"
                  id="hr-stage-select-trigger"
                  className="hr-stage-select-trigger"
                  aria-haspopup="listbox"
                  aria-expanded={hrStageMenuOpen}
                  aria-label="HR pipeline stage"
                  onClick={() => setHrStageMenuOpen((o) => !o)}
                  onKeyDown={(e) => {
                    if (e.key === 'Escape') setHrStageMenuOpen(false);
                  }}
                >
                  <span className="hr-stage-select-trigger-text">{selectedStageLabel}</span>
                  <span className={`hr-stage-select-chevron${hrStageMenuOpen ? ' is-open' : ''}`} aria-hidden>
                    ▼
                  </span>
                </button>
                {hrStageMenuOpen && (
                  <ul
                    className="hr-stage-select-menu"
                    role="listbox"
                    aria-labelledby="hr-stage-select-label"
                  >
                    {(HR_STAGE_DEFS as readonly HrStageDef[]).map((def: HrStageDef) => (
                      <li key={def.key} role="presentation">
                        <button
                          type="button"
                          role="option"
                          aria-selected={def.key === selectedHrStage}
                          className={
                            def.key === selectedHrStage
                              ? 'hr-stage-select-option is-selected'
                              : 'hr-stage-select-option'
                          }
                          onClick={() => {
                            setSelectedHrStage(def.key);
                            setHrStageMenuOpen(false);
                            setHrHistoryOpen(false);
                            setNewCommentText('');
                          }}
                        >
                          {def.label}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div className="hr-inline-status-group">
              <span className="hr-inline-status-label" id="hr-inline-status-label">
                Status
              </span>
              <div
                className="hr-application-status-radios-inline"
                role="radiogroup"
                aria-labelledby="hr-inline-status-label"
              >
                {APPLICATION_STATUS_OPTIONS.map(({ value, label }) => (
                  <label key={value} className="hr-application-status-radio-label">
                    <input
                      type="radio"
                      name="application-status"
                      value={value}
                      checked={headerApplicationStatus === value}
                      disabled={statusSaving}
                      onChange={() => void handleApplicationStatusChange(value)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
          {statusError && (
            <p className="hr-status-inline-error" role="alert">
              {statusError}
            </p>
          )}
          {selectedLatest && (
            <div
              className={`hr-stage-latest-block${selectedEarlier.length > 0 ? ' has-history' : ''}`}
              aria-live="polite"
              ref={hrLatestBlockRef}
            >
              <div className="hr-stage-latest-inner">
                <div className="hr-stage-latest-label">Latest</div>
                <time className="hr-stage-latest-meta" dateTime={selectedLatest.created_at}>
                  {formatDate(selectedLatest.created_at)}
                </time>
                <p className="hr-stage-latest-text">{selectedLatest.text}</p>
              </div>
              {selectedEarlier.length > 0 && (
                <div className="hr-stage-latest-actions">
                  <button
                    type="button"
                    className={`hr-stage-history-chevron${hrHistoryOpen ? ' is-open' : ''}`}
                    aria-expanded={hrHistoryOpen}
                    aria-label={`Earlier comments, ${selectedEarlier.length} entries`}
                    title="Earlier comments"
                    onClick={(e) => {
                      e.stopPropagation();
                      setHrHistoryOpen((o) => !o);
                    }}
                  >
                    <span aria-hidden>▼</span>
                  </button>
                  {hrHistoryOpen && (
                    <div className="hr-stage-history-dropdown" role="region" aria-label="Earlier comments">
                      <ul className="hr-stage-history-dropdown-list">
                        {selectedEarlier.map((e) => (
                          <li key={e.id} className="hr-stage-history-dropdown-item">
                            <time className="hr-stage-history-date" dateTime={e.created_at}>
                              {formatDate(e.created_at)}
                            </time>
                            <p className="hr-stage-history-text">{e.text}</p>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <label className="hr-comment-add-label" htmlFor="hr-comment-textarea">
            Add a comment
          </label>
          <textarea
            id="hr-comment-textarea"
            className="hr-comment-textarea"
            value={newCommentText}
            onChange={(e) => setNewCommentText(e.target.value)}
            placeholder={`Add an update for ${selectedStageLabel}…`}
            rows={4}
            maxLength={10000}
            aria-label={`New HR comment for ${selectedStageLabel}`}
          />
          <div className="hr-comment-footer">
            <button
              type="button"
              className="hr-comment-save-btn"
              onClick={() => void handleAddHrStageComment()}
              disabled={commentSaving || !newCommentText.trim()}
            >
              {commentSaving ? 'Adding…' : 'Add comment'}
            </button>
            {commentError && (
              <span className="hr-comment-error" role="alert">
                {commentError}
              </span>
            )}
          </div>
        </div>

        {/* Metadata */}
        <div className="detail-card">
          <h2>Metadata</h2>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Source file:</span>
              <span className="detail-value">{candidate.import_filename ?? '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Sheet:</span>
              <span className="detail-value">{candidate.import_sheet ?? '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Created At:</span>
              <span className="detail-value">{formatDate(candidate.created_at)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
