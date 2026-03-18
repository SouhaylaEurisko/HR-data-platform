import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getCandidateById, patchCandidateHrComment } from '../api/candidates';
import type { Candidate } from '../types/api';
import './CandidateDetailPage.css';

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const fromChat = (location.state as any)?.fromChat || false;

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
  const [commentDraft, setCommentDraft] = useState('');
  const [commentSaving, setCommentSaving] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);

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
        setCommentDraft(data.hr_comment ?? '');
      } catch (err: any) {
        setError(
          err.response?.data?.detail || err.message || 'Failed to load candidate details'
        );
      } finally {
        setLoading(false);
      }
    };
    fetchCandidate();
  }, [id]);

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

  const handleSaveHrComment = async () => {
    if (!candidate) return;
    setCommentSaving(true);
    setCommentError(null);
    try {
      const updated = await patchCandidateHrComment(candidate.id, commentDraft);
      setCandidate(updated);
      setCommentDraft(updated.hr_comment ?? '');
    } catch (err: any) {
      setCommentError(err.response?.data?.detail || err.message || 'Failed to save comment');
    } finally {
      setCommentSaving(false);
    }
  };

  return (
    <div className="candidate-detail-page">
      <div className="detail-header">
        <button onClick={goBack} className="back-button">
          &larr; {fromChat ? 'Back to Chat' : 'Back to Candidates'}
        </button>
        <h1>{displayName(candidate)}</h1>
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
                {candidate.is_open_for_relocation === true ? 'Yes' : candidate.is_open_for_relocation === false ? 'No' : '-'}
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

        {/* HR comment — below custom fields; save only when draft differs from saved */}
        <div className="detail-card detail-card-hr-comment">
          <div className="custom-fields-header">
            <h2>HR comment</h2>
          </div>
          <p className="hr-comment-hint">
            Internal notes for your team. This field is not filled from file uploads.
          </p>
          <textarea
            className="hr-comment-textarea"
            value={commentDraft}
            onChange={(e) => setCommentDraft(e.target.value)}
            placeholder="Add a comment about this candidate…"
            rows={5}
            maxLength={10000}
            aria-label="HR comment"
          />
          <div className="hr-comment-footer">
            <button
              type="button"
              className="hr-comment-save-btn"
              onClick={handleSaveHrComment}
              disabled={
                commentSaving ||
                commentDraft === (candidate.hr_comment ?? '')
              }
            >
              {commentSaving ? 'Saving…' : 'Save comment'}
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
