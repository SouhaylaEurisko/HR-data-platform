import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getCandidates } from '../api/candidates';
import type { Candidate, CandidateListParams } from '../types/api';
import './CandidatesPage.css';

export default function CandidatesPage() {
  const navigate = useNavigate();
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // Filter states
  const [filters, setFilters] = useState<CandidateListParams>({
    position: '',
    nationality: '',
    expected_salary: undefined,
    min_years_experience: undefined,
    max_years_experience: undefined,
    search: '',
    sort_by: 'created_at',
    sort_order: 'desc',
  });

  // Fetch candidates
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
    setPage(1); // Reset to first page when filter changes
  };

  const handleClearFilters = () => {
    setFilters({
      position: '',
      nationality: '',
      expected_salary: undefined,
      min_years_experience: undefined,
      max_years_experience: undefined,
      search: '',
      sort_by: 'created_at',
      sort_order: 'desc',
    });
    setPage(1);
  };

  const handleSort = (sortBy: 'created_at' | 'expected_salary' | 'years_experience') => {
    setFilters((prev) => ({
      ...prev,
      sort_by: sortBy,
      sort_order: prev.sort_by === sortBy && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const totalPages = Math.ceil(total / pageSize);

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

      {/* Filters Panel */}
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
              placeholder="Search candidates by name..."
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
              value={filters.position || ''}
              onChange={(e) => handleFilterChange('position', e.target.value)}
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
              placeholder="∞"
              value={filters.max_years_experience || ''}
              onChange={(e) =>
                handleFilterChange('max_years_experience', e.target.value ? parseFloat(e.target.value) : undefined)
              }
            />
          </div>

          <div className="filter-group">
            <label htmlFor="expected_salary">Expected Salary (USD)</label>
            <input
              id="expected_salary"
              type="number"
              min="0"
              step="100"
              placeholder="Exact amount"
              value={filters.expected_salary || ''}
              onChange={(e) =>
                handleFilterChange('expected_salary', e.target.value ? parseFloat(e.target.value) : undefined)
              }
            />
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {/* Candidates Table */}
      <div className="table-container">
        {loading ? (
          <div className="loading">Loading candidates...</div>
        ) : candidates.length === 0 ? (
          <div className="no-results">No candidates found matching your filters.</div>
        ) : (
          <table className="candidates-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('created_at')} className="sortable">
                  Name
                  {filters.sort_by === 'created_at' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th>Nationality</th>
                <th onClick={() => handleSort('years_experience')} className="sortable">
                  Experience
                  {filters.sort_by === 'years_experience' && (
                    <span className="sort-indicator">{filters.sort_order === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
                <th>Position</th>
                <th onClick={() => handleSort('expected_salary')} className="sortable">
                  Expected Salary
                  {filters.sort_by === 'expected_salary' && (
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
                  <td>{candidate.full_name || 'N/A'}</td>
                  <td>{candidate.nationality || 'N/A'}</td>
                  <td>
                    {candidate.years_experience !== null && candidate.years_experience !== undefined
                      ? `${candidate.years_experience} years`
                      : 'N/A'}
                  </td>
                  <td>{candidate.position || 'N/A'}</td>
                  <td>
                    {candidate.expected_salary_text && candidate.expected_salary_text.trim() !== ''
                      ? candidate.expected_salary_text
                      : candidate.expected_salary !== null && candidate.expected_salary !== undefined
                      ? `$${candidate.expected_salary.toLocaleString()}`
                      : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
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