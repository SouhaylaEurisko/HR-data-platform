import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getCandidates } from '../api/candidates';
import type { Candidate, CandidateListParams } from '../types/api';
import './CandidatesPage.css';

function parseSearchParams(sp: URLSearchParams) {
  return {
    page: Math.max(1, parseInt(sp.get('page') || '1', 10) || 1),
    filters: {
      applied_position: sp.get('applied_position') || '',
      nationality: sp.get('nationality') || '',
      min_years_experience: sp.get('min_years_experience') ? parseFloat(sp.get('min_years_experience')!) : undefined,
      max_years_experience: sp.get('max_years_experience') ? parseFloat(sp.get('max_years_experience')!) : undefined,
      search: sp.get('search') || '',
      sort_by: (sp.get('sort_by') as CandidateListParams['sort_by']) || 'created_at',
      sort_order: (sp.get('sort_order') as CandidateListParams['sort_order']) || 'desc',
    } as CandidateListParams,
  };
}

export default function CandidatesPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);

  const initial = parseSearchParams(searchParams);
  const [page, setPage] = useState(initial.page);
  const [pageSize] = useState(20);
  const [filters, setFilters] = useState<CandidateListParams>(initial.filters);
  const [showFixedFields, setShowFixedFields] = useState(false);

  const syncSearchParams = useCallback(
    (p: number, f: CandidateListParams) => {
      const params: Record<string, string> = {};
      if (p > 1) params.page = String(p);
      if (f.search) params.search = f.search;
      if (f.applied_position) params.applied_position = f.applied_position;
      if (f.nationality) params.nationality = f.nationality;
      if (f.min_years_experience !== undefined) params.min_years_experience = String(f.min_years_experience);
      if (f.max_years_experience !== undefined) params.max_years_experience = String(f.max_years_experience);
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
          Object.entries(filters).filter(([_, v]) => v !== '' && v !== undefined)
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
      nationality: '',
      min_years_experience: undefined,
      max_years_experience: undefined,
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

  return (
    <div className="candidates-page">
      <div className="page-top-bar">
        <div className="candidates-header">
          <h1>Candidates</h1>
          <p className="candidates-count">
            {loading ? 'Loading...' : `Showing ${candidates.length} of ${total} candidates`}
          </p>
        </div>
        <button onClick={() => navigate('/upload')} className="cross-nav-btn">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
          </svg>
          Upload Data
        </button>
      </div>

      <div className="filters-panel">
        <div className="filters-header">
          <h2>Filters</h2>
          <button onClick={handleClearFilters} className="clear-filters-btn">
            Clear All
          </button>
        </div>

        <div className="filters-grid">
          <div className="filter-group">
            <label htmlFor="search">Search by Name</label>
            <input
              id="search"
              type="text"
              placeholder="Search candidates..."
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
          <div className="filter-group">
            <label htmlFor="nationality">Nationality</label>
            <input
              id="nationality"
              type="text"
              placeholder="e.g. Lebanese"
              value={filters.nationality || ''}
              onChange={(e) => handleFilterChange('nationality', e.target.value)}
            />
          </div>
        </div>

        <div className="filter-toggles">
          <button
            type="button"
            className="filter-toggle-btn"
            onClick={() => setShowFixedFields((v) => !v)}
            aria-expanded={showFixedFields}
          >
            {showFixedFields ? '▼' : '▶'} Show more fields
          </button>
        </div>

        {showFixedFields && (
          <div className="filters-grid filters-fixed">
            <div className="filter-group">
              <label htmlFor="min_years">Min Years Experience</label>
              <input
                id="min_years"
                type="number"
                min="0"
                step="0.5"
                placeholder="0"
                value={filters.min_years_experience || ''}
                onChange={(e) =>
                  handleFilterChange('min_years_experience', e.target.value ? parseFloat(e.target.value) : undefined)
                }
              />
            </div>
            <div className="filter-group">
              <label htmlFor="max_years">Max Years Experience</label>
              <input
                id="max_years"
                type="number"
                min="0"
                step="0.5"
                placeholder="No limit"
                value={filters.max_years_experience || ''}
                onChange={(e) =>
                  handleFilterChange('max_years_experience', e.target.value ? parseFloat(e.target.value) : undefined)
                }
              />
            </div>
          </div>
        )}
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
                <th>Nationality</th>
                <th onClick={() => handleSort('years_of_experience')} className="sortable">
                  Experience
                  {filters.sort_by === 'years_of_experience' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th onClick={() => handleSort('applied_position')} className="sortable">
                  Position
                  {filters.sort_by === 'applied_position' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th onClick={() => handleSort('current_salary')} className="sortable">
                  Current Salary
                  {filters.sort_by === 'current_salary' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th onClick={() => handleSort('expected_salary_remote')} className="sortable">
                  Expected Salary (Remote)
                  {filters.sort_by === 'expected_salary_remote' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th onClick={() => handleSort('expected_salary_onsite')} className="sortable">
                  Expected Salary (Onsite)
                  {filters.sort_by === 'expected_salary_onsite' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr
                  key={candidate.id}
                  onClick={() => navigate(`/candidates/${candidate.id}`)}
                  className="table-row-clickable"
                >
                  <td>{displayName(candidate)}</td>
                  <td>{candidate.nationality || 'N/A'}</td>
                  <td>
                    {candidate.years_of_experience !== null && candidate.years_of_experience !== undefined
                      ? `${candidate.years_of_experience} years`
                      : 'N/A'}
                  </td>
                  <td>{candidate.applied_position || 'N/A'}</td>
                  <td>
                    {candidate.current_salary !== null && candidate.current_salary !== undefined
                      ? `$${Number(candidate.current_salary).toLocaleString()}`
                      : 'N/A'}
                  </td>
                  <td>
                    {candidate.expected_salary_remote !== null && candidate.expected_salary_remote !== undefined
                      ? `$${Number(candidate.expected_salary_remote).toLocaleString()}`
                      : 'N/A'}
                  </td>
                  <td>
                    {candidate.expected_salary_onsite !== null && candidate.expected_salary_onsite !== undefined
                      ? `$${Number(candidate.expected_salary_onsite).toLocaleString()}`
                      : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
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
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="pagination-btn"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
