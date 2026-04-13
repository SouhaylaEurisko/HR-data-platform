import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import ApplicationStatusBadge from '../components/ApplicationStatusBadge';
import { fetchLookupOptions } from '../api/lookups';
import {
  getCandidateById,
  patchCandidateApplicationStatus,
  postCandidateHrStageComment,
  getResume,
  uploadResume,
  downloadResume,
  deleteResume,
  deleteCandidate,
} from '../api/candidates';
import { APPLICATION_STATUS_OPTIONS, parseApplicationStatus } from '../constants/applicationStatus';
import {
  HR_STAGE_DEFS,
  latestStageComment,
  type HrStageDef,
  type HrStageKey,
} from '../constants/hrStages.ts';
import type { ApplicationStatus, Candidate, CandidateResume, HrStageCommentEntry, LookupOption } from '../types/api';
import { apiErrorMessage } from '../utils/apiErrorMessage';
import { PersonalInformationCard, ProfessionalInformationCard } from '../components/CandidateDetailEditableCards';
import { useAuth } from '../contexts/AuthContext';
import ConfirmationDialog from '../components/ConfirmationDialog';
import {
  formatResumeMismatchMessage,
  getResumeCandidateIdentityMismatch,
} from '../utils/resumeIdentityMatch';
import './CandidateDetailPage.css';

function entriesForStage(c: Candidate, key: HrStageKey): HrStageCommentEntry[] {
  const s = c.hr_stage_comments?.[key];
  return Array.isArray(s) ? s : [];
}

type CandidateDetailLocationState = {
  fromChat?: boolean;
  focusHrComment?: boolean;
  /** Query string from candidates list (no leading `?`) — restores page & filters when leaving detail. */
  candidatesListSearch?: string;
};

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { canWrite } = useAuth();
  const fromChat =
    (location.state as CandidateDetailLocationState | null)?.fromChat ?? false;

  const goBack = () => {
    if (fromChat) {
      navigate('/chat');
      return;
    }
    const qs = (location.state as CandidateDetailLocationState | null)?.candidatesListSearch?.trim();
    if (qs) {
      navigate({ pathname: '/candidates', search: `?${qs}` });
    } else {
      navigate('/candidates');
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
  const [resume, setResume] = useState<CandidateResume | null>(null);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [pdfViewerUrl, setPdfViewerUrl] = useState<string | null>(null);
  const [resumeMismatchOpen, setResumeMismatchOpen] = useState(false);
  const [resumeMismatchMessage, setResumeMismatchMessage] = useState('');
  const resumeFileRef = useRef<HTMLInputElement>(null);
  const didScrollToHrComment = useRef(false);
  const [lookupOptions, setLookupOptions] = useState<Record<string, LookupOption[]>>({});
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
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
    if (!canWrite) return;
    const codes = [
      'residency_type',
      'marital_status',
      'passport_validity',
      'workplace_type',
      'employment_type',
      'education_level',
      'education_completion',
    ] as const;
    let cancelled = false;
    void (async () => {
      try {
        const pairs = await Promise.all(
          codes.map(async (code) => {
            const opts = await fetchLookupOptions(code);
            return [code, opts] as const;
          })
        );
        if (cancelled) return;
        const next: Record<string, LookupOption[]> = {};
        for (const [code, opts] of pairs) next[code] = opts;
        setLookupOptions(next);
      } catch {
        if (!cancelled) setLookupOptions({});
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [canWrite]);

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
    if (!id) return;
    const candidateId = parseInt(id, 10);
    if (isNaN(candidateId)) return;
    setResumeLoading(true);
    getResume(candidateId)
      .then((r) => setResume(r))
      .catch(() => setResume(null))
      .finally(() => setResumeLoading(false));
  }, [id]);

  const handleResumeUpload = async (file: File) => {
    if (!candidate) return;
    setResumeUploading(true);
    setResumeError(null);
    try {
      const r = await uploadResume(candidate.id, file);
      setResume(r);
      const mismatch = getResumeCandidateIdentityMismatch(candidate, r.resume_info);
      if (mismatch) {
        setResumeMismatchMessage(formatResumeMismatchMessage(mismatch));
        setResumeMismatchOpen(true);
      }
    } catch (err: unknown) {
      setResumeError(apiErrorMessage(err, 'Failed to upload resume'));
    } finally {
      setResumeUploading(false);
    }
  };

  const handleResumeDownload = async () => {
    if (!candidate || !resume) return;
    try {
      const blob = await downloadResume(candidate.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = resume.filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setResumeError(apiErrorMessage(err, 'Failed to download resume'));
    }
  };

  const handleViewPdf = async () => {
    if (!candidate || !resume) return;
    try {
      const blob = await downloadResume(candidate.id);
      const url = URL.createObjectURL(blob);
      setPdfViewerUrl(url);
    } catch (err: unknown) {
      setResumeError(apiErrorMessage(err, 'Failed to load PDF preview'));
    }
  };

  const closePdfViewer = () => {
    if (pdfViewerUrl) {
      URL.revokeObjectURL(pdfViewerUrl);
      setPdfViewerUrl(null);
    }
  };

  const handleResumeDelete = async () => {
    if (!candidate) return;
    setResumeError(null);
    try {
      await deleteResume(candidate.id);
      setResume(null);
    } catch (err: unknown) {
      setResumeError(apiErrorMessage(err, 'Failed to delete resume'));
    }
  };

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
      if (canWrite) {
        document.getElementById('hr-stage-select-trigger')?.focus();
      }
    };
    requestAnimationFrame(() => setTimeout(run, 50));
    navigate(location.pathname, {
      replace: true,
      state: {
        fromChat: st.fromChat,
        candidatesListSearch: st.candidatesListSearch,
      },
    });
  }, [candidate, location.pathname, location.state, navigate, canWrite]);

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
          <div className="detail-header-left">
            <h1>{displayName(candidate)}</h1>
            <ApplicationStatusBadge status={headerApplicationStatus} size="large" />
          </div>
          <div className="detail-header-cv">
            <input
              ref={resumeFileRef}
              type="file"
              accept=".pdf"
              className="resume-file-input"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleResumeUpload(file);
              }}
            />
            {resumeLoading ? (
              <span className="cv-btn cv-btn-loading">Loading CV...</span>
            ) : resume ? (
              <>
                <button type="button" className="cv-btn cv-btn-view" onClick={() => void handleViewPdf()}>
                  <svg viewBox="0 0 20 20" fill="currentColor" className="cv-icon">
                    <path d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" />
                  </svg>
                  View CV
                </button>
                <button type="button" className="cv-btn cv-btn-download" onClick={handleResumeDownload}>
                  <svg viewBox="0 0 20 20" fill="currentColor" className="cv-icon">
                    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                  Download
                </button>
                {canWrite && (
                  <>
                    <button
                      type="button"
                      className="cv-btn cv-btn-replace"
                      disabled={resumeUploading}
                      onClick={() => resumeFileRef.current?.click()}
                    >
                      {resumeUploading ? 'Uploading...' : 'Replace'}
                    </button>
                    <button type="button" className="cv-btn cv-btn-delete" onClick={handleResumeDelete}>
                      Delete
                    </button>
                  </>
                )}
              </>
            ) : canWrite ? (
              <button
                type="button"
                className="cv-btn cv-btn-upload"
                disabled={resumeUploading}
                onClick={() => resumeFileRef.current?.click()}
              >
                <svg viewBox="0 0 20 20" fill="currentColor" className="cv-icon">
                  <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
                {resumeUploading ? 'Uploading...' : 'Upload CV'}
              </button>
            ) : (
              <span className="cv-btn cv-btn-none">No CV</span>
            )}
            {resumeError && <span className="cv-error">{resumeError}</span>}
          </div>
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
                              onClick={() =>
                                navigate(`/candidates/${r.id}`, { state: location.state ?? undefined })
                              }
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
        {!canWrite && (
          <div className="read-only-banner" role="status">
            Read-only access: you can view candidates and HR comments. Only HR managers can edit profile
            fields, change application status, add comments, or delete a candidate.
          </div>
        )}
        <PersonalInformationCard
          candidate={candidate}
          canWrite={canWrite}
          lookups={lookupOptions}
          onCandidateUpdated={setCandidate}
          formatDate={formatDate}
          displayName={displayName}
        />
        <ProfessionalInformationCard
          candidate={candidate}
          canWrite={canWrite}
          lookups={lookupOptions}
          onCandidateUpdated={setCandidate}
          formatDate={formatDate}
          displayName={displayName}
        />

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
            {canWrite
              ? 'Add a comment and track your comment history for each stage.'
              : 'View comments by stage below. Adding comments requires an HR manager role.'}
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
                      disabled={statusSaving || !canWrite}
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
          {canWrite ? (
            <>
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
            </>
          ) : null}
        </div>

        {/* Resume / CV — Parsed Info (always visible when resume exists) */}
        {resume && (
          <div className="detail-card detail-card-resume-panel">
            <h2>Resume / CV — Info</h2>

            {(() => {
              const ri = resume.resume_info;
              const hasData = ri && (
                ri.summary ||
                (ri.skills && ri.skills.length > 0) ||
                (ri.languages && ri.languages.length > 0) ||
                (ri.work_experience && ri.work_experience.length > 0) ||
                (ri.education && ri.education.length > 0) ||
                (ri.certifications && ri.certifications.length > 0)
              );

              if (!hasData) {
                return (
                  <p className="resume-empty-info">
                    No parsed data available. The CV was uploaded but automatic extraction did not
                    produce results. This can happen if the server lacks PyMuPDF or if the PDF
                    format could not be read. You can still view the original PDF using "View CV".
                  </p>
                );
              }

              return (
                <div className="resume-info-grid">
                  {ri.summary && (
                    <div className="resume-info-section">
                      <h3>Summary</h3>
                      <p>{ri.summary}</p>
                    </div>
                  )}

                  {ri.skills && ri.skills.length > 0 && (
                    <div className="resume-info-section">
                      <h3>Skills</h3>
                      <div className="resume-tags">
                        {ri.skills.map((s, i) => (
                          <span key={i} className="resume-tag">{s}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {ri.languages && ri.languages.length > 0 && (
                    <div className="resume-info-section">
                      <h3>Languages</h3>
                      <div className="resume-tags">
                        {ri.languages.map((l, i) => (
                          <span key={i} className="resume-tag">{l}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {ri.work_experience && ri.work_experience.length > 0 && (
                    <div className="resume-info-section">
                      <h3>Work Experience</h3>
                      <ul className="resume-timeline">
                        {ri.work_experience.map((w, i) => (
                          <li key={i} className="resume-timeline-item">
                            <strong>{w.title || 'Untitled'}</strong>
                            {w.company && <span className="resume-company"> at {w.company}</span>}
                            {(w.start_date || w.end_date) && (
                              <span className="resume-dates">
                                {' '}({w.start_date || '?'} – {w.end_date || 'Present'})
                              </span>
                            )}
                            {w.description && <p className="resume-desc">{w.description}</p>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {ri.education && ri.education.length > 0 && (
                    <div className="resume-info-section">
                      <h3>Education</h3>
                      <ul className="resume-timeline">
                        {ri.education.map((e, i) => (
                          <li key={i} className="resume-timeline-item">
                            <strong>{e.degree || 'Degree'}</strong>
                            {e.field_of_study && <span> in {e.field_of_study}</span>}
                            {e.institution && <span className="resume-company"> — {e.institution}</span>}
                            {(e.start_date || e.end_date) && (
                              <span className="resume-dates">
                                {' '}({e.start_date || '?'} – {e.end_date || 'Present'})
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {ri.certifications && ri.certifications.length > 0 && (
                    <div className="resume-info-section">
                      <h3>Certifications</h3>
                      <div className="resume-tags">
                        {ri.certifications.map((c, i) => (
                          <span key={i} className="resume-tag">{c}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}

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

      {canWrite && (
        <button
          type="button"
          className="candidate-detail-delete-corner"
          aria-label="Delete candidate"
          onClick={() => {
            setDeleteError(null);
            setDeleteDialogOpen(true);
          }}
        >
          Delete candidate
        </button>
      )}

      {/* PDF Viewer Modal */}
      {pdfViewerUrl && (
        <div className="pdf-viewer-overlay" onClick={closePdfViewer}>
          <div className="pdf-viewer-modal" onClick={(e) => e.stopPropagation()}>
            <div className="pdf-viewer-header">
              <span className="pdf-viewer-title">{resume?.filename ?? 'Resume'}</span>
              <button type="button" className="pdf-viewer-close" onClick={closePdfViewer}>
                ✕
              </button>
            </div>
            <iframe
              className="pdf-viewer-iframe"
              src={pdfViewerUrl}
              title="Resume PDF"
            />
          </div>
        </div>
      )}

      <ConfirmationDialog
        isOpen={resumeMismatchOpen}
        title="CV may not match this candidate"
        message={resumeMismatchMessage}
        variant="warning"
        singleButton
        confirmText="OK"
        onConfirm={() => setResumeMismatchOpen(false)}
        onCancel={() => setResumeMismatchOpen(false)}
      />

      <ConfirmationDialog
        isOpen={deleteDialogOpen}
        title="Delete this candidate?"
        message={
          deleteError
            ? deleteError
            : `This will permanently delete ${displayName(candidate)} and all related data in this platform: application rows, uploaded CV, and HR stage comments. This cannot be undone.`
        }
        variant="danger"
        confirmText={deleteBusy ? 'Deleting…' : 'Delete candidate'}
        cancelText="Cancel"
        onCancel={() => {
          if (!deleteBusy) {
            setDeleteDialogOpen(false);
            setDeleteError(null);
          }
        }}
        onConfirm={() => {
          if (deleteBusy) return;
          void (async () => {
            setDeleteBusy(true);
            setDeleteError(null);
            try {
              await deleteCandidate(candidate.id);
              setDeleteDialogOpen(false);
              goBack();
            } catch (e: unknown) {
              setDeleteError(apiErrorMessage(e, 'Failed to delete candidate'));
            } finally {
              setDeleteBusy(false);
            }
          })();
        }}
      />
    </div>
  );
}
