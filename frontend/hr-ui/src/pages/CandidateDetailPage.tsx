import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getCandidateById } from '../api/candidates';
import type { Candidate } from '../types/api';
import './CandidateDetailPage.css';

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const fromChat = (location.state as any)?.fromChat || false;

  /** Navigate back preserving the page the user came from. */
  const goBack = () => {
    if (fromChat) {
      navigate('/chat');
    } else {
      // Use browser history so the CandidatesPage URL (with ?page=…) is restored
      navigate(-1);
    }
  };
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRawData, setShowRawData] = useState(false);

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
    if (!dateString) return 'N/A';
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
        <button
          onClick={goBack}
          className="back-button"
        >
          ← {fromChat ? 'Back to Chat' : 'Back to Candidates'}
        </button>
      </div>
    );
  }

  return (
    <div className="candidate-detail-page">
      <div className="detail-header">
        <button
          onClick={goBack}
          className="back-button"
        >
          ← {fromChat ? 'Back to Chat' : 'Back to Candidates'}
        </button>
        <h1>Candidate Details</h1>
      </div>

      <div className="detail-content">
        {/* Main Information Card */}
        <div className="detail-card">
          <h2>Personal Information</h2>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Full Name:</span>
              <span className="detail-value">{candidate.full_name || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Email:</span>
              <span className="detail-value">
                {candidate.email ? (
                  <a href={`mailto:${candidate.email}`}>{candidate.email}</a>
                ) : (
                  'N/A'
                )}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Nationality:</span>
              <span className="detail-value">{candidate.nationality || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Date of Birth:</span>
              <span className="detail-value">{formatDate(candidate.date_of_birth)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Current Address:</span>
              <span className="detail-value">{candidate.current_address || 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Professional Information Card */}
        <div className="detail-card">
          <h2>Professional Information</h2>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Position:</span>
              <span className="detail-value">{candidate.position || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Years of Experience:</span>
              <span className="detail-value">
                {candidate.years_experience !== null && candidate.years_experience !== undefined
                  ? `${candidate.years_experience} years`
                  : 'N/A'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Expected Salary:</span>
              <span className="detail-value">
                {candidate.expected_salary_text && candidate.expected_salary_text.trim() !== ''
                  ? candidate.expected_salary_text
                  : candidate.expected_salary !== null && candidate.expected_salary !== undefined
                  ? `$${candidate.expected_salary.toLocaleString()} USD`
                  : 'N/A'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Notice Period:</span>
              <span className="detail-value">{candidate.notice_period || 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Supplementary Information Card */}
        {candidate.raw_data && (
          <div className="detail-card">
            <div className="raw-data-header">
              <h2>Supplementary Information</h2>
              <button
                onClick={() => setShowRawData(!showRawData)}
                className="toggle-raw-data-btn"
              >
                {showRawData ? 'Hide' : 'Show'} Details
              </button>
            </div>
            {showRawData && (
              <div className="raw-data-content">
                <dl>
                  {Object.entries(candidate.raw_data).map(([key, value]) => (
                    <div className="raw-data-row" key={key}>
                      <dt className="raw-data-key">{key}</dt>
                      <dd className="raw-data-value">
                        {value === null || value === undefined || value === ''
                          ? 'N/A'
                          : String(value)}
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            )}
          </div>
        )}

        {/* Metadata Card */}
        <div className="detail-card">
          <h2>Metadata</h2>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Source File:</span>
              <span className="detail-value">{candidate.source_file || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Sheet:</span>
              <span className="detail-value">{candidate.source_sheet || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Created At:</span>
              <span className="detail-value">{formatDate(candidate.created_at)}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Last Updated:</span>
              <span className="detail-value">{formatDate(candidate.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
