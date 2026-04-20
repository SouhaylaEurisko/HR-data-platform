import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ApplicationStatusBadge from '../components/ApplicationStatusBadge';
import ConfirmationDialog from '../components/ConfirmationDialog';
import { deleteCandidate, getCandidates } from '../api/candidates';
import { useAuth } from '../contexts/AuthContext';
import { parseApplicationStatus } from '../constants/applicationStatus';
import { HR_STAGE_DEFS, emptyHrStageCommentLists, latestStageComment } from '../constants/hrStages';
import type { Candidate, CandidateListParams } from '../types/api';
import { apiErrorMessage } from '../utils/apiErrorMessage';
import { relocationOpennessLabel } from '../utils/relocationOpenness';
import './CandidatesPage.css';

function hrCommentsListSummary(candidate: Candidate): { full: string; short: string } {
  const hc = candidate.hr_stage_comments ?? emptyHrStageCommentLists();
  const parts: string[] = [];
  for (const { key, label } of HR_STAGE_DEFS) {
    const latest = latestStageComment(hc[key]);
    const t = (latest?.text ?? '').trim();
    if (t) parts.push(`${label}: ${t}`);
  }
  const full = parts.join(' · ');
  const short = full.length > 72 ? `${full.slice(0, 72)}…` : full;
  return { full, short };
}

function parseSearchParams(sp: URLSearchParams) {
  return {
    page: Math.max(1, parseInt(sp.get('page') || '1', 10) || 1),
    filters: {
      applied_position: sp.get('applied_position') || '',
      search: sp.get('search') || '',
      sort_by: (sp.get('sort_by') as CandidateListParams['sort_by']) || 'created_at',
      sort_order: (sp.get('sort_order') as CandidateListParams['sort_order']) || 'desc',
    } as CandidateListParams,
  };
}

export default function CandidatesPage() {
  const navigate = useNavigate();
  const { canWrite } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const listSearchSnapshot = searchParams.toString();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<Candidate | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const initial = parseSearchParams(searchParams);
  const [page, setPage] = useState(initial.page);
  const [pageSize] = useState(20);
  const [filters, setFilters] = useState<CandidateListParams>(initial.filters);

  const syncSearchParams = useCallback(
    (p: number, f: CandidateListParams) => {
      const params: Record<string, string> = {};
      if (p > 1) params.page = String(p);
      if (f.search) params.search = f.search;
      if (f.applied_position) params.applied_position = f.applied_position;
      if (f.sort_by && f.sort_by !== 'created_at') params.sort_by = f.sort_by;
      if (f.sort_order && f.sort_order !== 'desc') params.sort_order = f.sort_order;
      setSearchParams(params, { replace: true });
    },
    [setSearchParams],
  );

  useEffect(() => {
    syncSearchParams(page, filters);
  }, [page, filters, syncSearchParams]);

  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const params: CandidateListParams = {
        page,
        page_size: pageSize,
        ...Object.fromEntries(
          Object.entries(filters).filter(([_, v]) => v !== '' && v !== undefined),
        ),
      };
      const response = await getCandidates(params);
      setCandidates(response.items);
      setTotal(response.total);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load candidates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, filters]);

  const handleFilterChange = (key: keyof CandidateListParams, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const handleClearFilters = () => {
    setFilters({
      applied_position: '',
      search: '',
      sort_by: 'created_at',
      sort_order: 'desc',
    });
    setPage(1);
  };

  const handleSort = (sortBy: CandidateListParams['sort_by']) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: sortBy,
      sort_order: prev.sort_by === sortBy && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const totalPages = Math.ceil(total / pageSize);

  const displayName = (c: Candidate) => c.full_name || 'N/A';

  const willingToRelocate = (c: Candidate) =>
    relocationOpennessLabel(c.is_open_for_relocation);
  const deleteTargetName = deleteTarget ? displayName(deleteTarget) : 'this candidate';

  const handleDeleteCandidate = async () => {
    if (!deleteTarget || deleteBusy) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await deleteCandidate(deleteTarget.id, deleteTarget.organization_id);
      setDeleteTarget(null);
      setCandidates((prev) => prev.filter((c) => c.id !== deleteTarget.id));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (err: unknown) {
      setDeleteError(apiErrorMessage(err, 'Failed to delete candidate'));
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <div className="candidates-page">
      <div className="page-top-bar">
        <div className="candidates-header">
          <h1>Candidates</h1>
          <p className="candidates-count">
            {loading ? 'Loading...' : `Showing ${candidates.length} of ${total} candidates`}
          </p>
        </div>
        {canWrite && (
          <button type="button" onClick={() => navigate('/upload')} className="cross-nav-btn">
            <svg viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
            Upload Data
          </button>
        )}
      </div>

      <div className="filters-panel">
        <div className="filters-header">
          <h2>Filters</h2>
          <button type="button" onClick={handleClearFilters} className="clear-filters-btn">
            Clear All
          </button>
        </div>

        <div className="filters-grid filters-grid-two">
          <div className="filter-group">
            <label htmlFor="search">Search by name</label>
            <input
              id="search"
              type="text"
              placeholder="Type a name…"
              value={filters.search || ''}
              onChange={(e) => handleFilterChange('search', e.target.value)}
            />
          </div>
          <div className="filter-group">
            <label htmlFor="position">Position</label>
            <input
              id="position"
              type="text"
              placeholder="e.g. Backend Engineer"
              value={filters.applied_position || ''}
              onChange={(e) => handleFilterChange('applied_position', e.target.value)}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      <div className="table-container">
        {loading ? (
          <div className="loading">Loading candidates...</div>
        ) : candidates.length === 0 ? (
          <div className="no-results">No candidates found matching your filters.</div>
        ) : (
          <table className="candidates-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('full_name')} className="sortable">
                  Name
                  {filters.sort_by === 'full_name' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th onClick={() => handleSort('applied_position')} className="sortable">
                  Position
                  {filters.sort_by === 'applied_position' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th>Willing to relocate</th>
                <th>Status</th>
                <th>HR comments</th>
                {canWrite && <th className="actions-col">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => {
                const { full, short } = hrCommentsListSummary(candidate);
                const appStatus = parseApplicationStatus(candidate.application_status);
                return (
                  <tr
                    key={candidate.id}
                    onClick={() =>
                      navigate(`/candidates/${candidate.id}`, {
                        state: { candidatesListSearch: listSearchSnapshot },
                      })
                    }
                    className="table-row-clickable"
                  >
                    <td>{displayName(candidate)}</td>
                    <td>{candidate.applied_position || '—'}</td>
                    <td>{willingToRelocate(candidate)}</td>
                    <td className="td-application-status" onClick={(e) => e.stopPropagation()}>
                      {appStatus ? (
                        <ApplicationStatusBadge status={appStatus} />
                      ) : (
                        <span className="td-status-empty">—</span>
                      )}
                    </td>
                    <td className="td-hr-comment" title={full || undefined}>
                      {full ? (
                        short
                      ) : canWrite ? (
                        <button
                          type="button"
                          className="hr-comment-add-trigger"
                          aria-label={`Add HR comments for ${displayName(candidate)}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/candidates/${candidate.id}`, {
                              state: {
                                focusHrComment: true,
                                candidatesListSearch: listSearchSnapshot,
                              },
                            });
                          }}
                        >
                          +
                        </button>
                      ) : (
                        <span className="td-status-empty">—</span>
                      )}
                    </td>
                    {canWrite && (
                      <td className="td-actions" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          className="candidate-delete-icon-btn"
                          aria-label={`Delete ${displayName(candidate)}`}
                          onClick={() => {
                            setDeleteError(null);
                            setDeleteTarget(candidate);
                          }}
                        >
                          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                            <path
                              d="M4 7h16M10 3h4a1 1 0 011 1v2H9V4a1 1 0 011-1zm-2 4h8l-1 12a1 1 0 01-1 .9h-4a1 1 0 01-1-.9L8 7z"
                              stroke="currentColor"
                              strokeWidth="1.6"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            />
                          </svg>
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="pagination-btn"
          >
            Previous
          </button>
          <span className="pagination-info">
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="pagination-btn"
          >
            Next
          </button>
        </div>
      )}

      <ConfirmationDialog
        isOpen={deleteTarget != null}
        title="Delete this candidate?"
        message={
          deleteError ??
          `This will permanently remove ${deleteTargetName}. This action cannot be undone.`
        }
        variant="danger"
        confirmText={deleteBusy ? 'Deleting…' : 'Delete'}
        cancelText="Cancel"
        onCancel={() => {
          if (!deleteBusy) {
            setDeleteTarget(null);
            setDeleteError(null);
          }
        }}
        onConfirm={() => {
          void handleDeleteCandidate();
        }}
      />
    </div>
  );
}
