import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { getAnalyticsOverview } from '../api/analytics';
import { applicationStatusLabel, parseApplicationStatus } from '../constants/applicationStatus';
import type {
  AnalyticsFilterOption,
  AnalyticsNamedCount,
  AnalyticsOverview,
  AnalyticsPositionAverage,
} from '../types/api';
import './AnalyticsPage.css';

type AnalyticsPageFilters = {
  status: string;
  position: string;
  location: string;
};

const EMPTY_FILTERS: AnalyticsPageFilters = {
  status: '',
  position: '',
  location: '',
};

function formatInt(n: number): string {
  return n.toLocaleString();
}

function normalizeAnalyticsOverview(raw: AnalyticsOverview): AnalyticsOverview {
  return {
    total_candidates: raw.total_candidates ?? 0,
    recent_applications_30d: raw.recent_applications_30d ?? 0,
    candidates_with_resume: raw.candidates_with_resume ?? 0,
    resume_coverage_percent: raw.resume_coverage_percent ?? 0,
    by_application_status: raw.by_application_status ?? [],
    top_applied_positions: raw.top_applied_positions ?? [],
    top_locations: raw.top_locations ?? [],
    avg_expected_salary_by_position: raw.avg_expected_salary_by_position ?? [],
    avg_years_experience_by_position: raw.avg_years_experience_by_position ?? [],
    filter_options: {
      statuses: raw.filter_options?.statuses ?? [],
      positions: raw.filter_options?.positions ?? [],
      locations: raw.filter_options?.locations ?? [],
    },
    applied_filters: {
      status: raw.applied_filters?.status ?? null,
      position: raw.applied_filters?.position ?? null,
      location: raw.applied_filters?.location ?? null,
    },
  };
}

/** Canonical key for pipeline colors; API uses human labels ("On hold") not enum values (on_hold). */
function canonicalPipelineStatusKey(raw: string): string {
  const t = raw.trim();
  if (!t) return '';
  const lower = t.toLowerCase();
  if (lower === 'unset' || lower === 'not set') return 'unset';
  const slug = lower.replace(/[\s-]+/g, '_');
  return parseApplicationStatus(slug) ?? parseApplicationStatus(lower) ?? slug;
}

function pipelineStatusLabel(key: string): string {
  const k = canonicalPipelineStatusKey(key);
  if (k === 'unset') return 'Not set';
  const parsed = parseApplicationStatus(k);
  return parsed ? applicationStatusLabel(parsed) : key;
}

const PIPELINE_COLORS: Record<string, string> = {
  pending: '#eab308',
  on_hold: '#94a3b8',
  rejected: '#ef4444',
  selected: '#22c55e',
  unset: '#a78bfa',
};

const PIPELINE_FALLBACK_PALETTE = ['#c084fc', '#38bdf8', '#fb923c', '#f472b6', '#94a3b8'];

function pipelineColor(name: string, index: number): string {
  const k = canonicalPipelineStatusKey(name);
  return PIPELINE_COLORS[k] ?? PIPELINE_FALLBACK_PALETTE[index % PIPELINE_FALLBACK_PALETTE.length];
}

/** t ∈ [0,1]: clockwise from top (12 o'clock). */
function pointOnCircle(cx: number, cy: number, r: number, t: number): { x: number; y: number } {
  const deg = -90 + 360 * t;
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/** Donut slice from fraction t0 → t1 with slight gaps between slices. */
function donutSlicePath(
  cx: number,
  cy: number,
  rOuter: number,
  rInner: number,
  t0: number,
  t1: number,
): string | null {
  const span = t1 - t0;
  if (span <= 0) return null;
  const pad = Math.min(0.007, span * 0.12);
  const a0 = t0 + pad;
  const a1 = t1 - pad;
  if (a1 - a0 < 0.0005) return null;

  const p1 = pointOnCircle(cx, cy, rOuter, a0);
  const p2 = pointOnCircle(cx, cy, rOuter, a1);
  const p3 = pointOnCircle(cx, cy, rInner, a1);
  const p4 = pointOnCircle(cx, cy, rInner, a0);
  const sweep = a1 - a0;
  const large = sweep > 0.5 ? 1 : 0;

  return [
    `M ${p1.x.toFixed(3)} ${p1.y.toFixed(3)}`,
    `A ${rOuter} ${rOuter} 0 ${large} 1 ${p2.x.toFixed(3)} ${p2.y.toFixed(3)}`,
    `L ${p3.x.toFixed(3)} ${p3.y.toFixed(3)}`,
    `A ${rInner} ${rInner} 0 ${large} 0 ${p4.x.toFixed(3)} ${p4.y.toFixed(3)}`,
    'Z',
  ].join(' ');
}

function PipelineDonut({ items = [], total }: { items?: AnalyticsNamedCount[]; total: number }) {
  const filterId = useId().replace(/:/g, '');

  const paths = useMemo(() => {
    if (total <= 0 || !items.length) return [];
    const cx = 50;
    const cy = 50;
    const rOuter = 39;
    const rInner = 24.5;
    let cum = 0;
    const out: { d: string; fill: string; key: string }[] = [];
    items.forEach((item, i) => {
      const t0 = cum / total;
      const t1 = (cum + item.count) / total;
      cum += item.count;
      const d = donutSlicePath(cx, cy, rOuter, rInner, t0, t1);
      if (d) {
        out.push({ d, fill: pipelineColor(item.name, i), key: `${item.name}-${i}` });
      }
    });
    return out;
  }, [items, total]);

  if (total <= 0) {
    return (
      <div className="analytics-donut analytics-donut--empty" aria-hidden>
        <div className="analytics-donut-hole">
          <span className="analytics-donut-total">0</span>
        </div>
      </div>
    );
  }

  if (paths.length === 0) {
    return (
      <div className="analytics-donut analytics-donut--empty" aria-hidden>
        <div className="analytics-donut-hole">
          <span className="analytics-donut-total">—</span>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-donut-wrap">
      <div className="analytics-donut-ring analytics-donut-ring--strong" aria-hidden />
      <div className="analytics-donut analytics-donut--svg">
        <svg
          className="analytics-donut-svg"
          viewBox="0 0 100 100"
          role="img"
          aria-label="Pipeline distribution chart"
        >
          <defs>
            <filter
              id={filterId}
              x="-35%"
              y="-35%"
              width="170%"
              height="170%"
              colorInterpolationFilters="sRGB"
            >
              <feGaussianBlur in="SourceAlpha" stdDeviation="0.8" result="blur" />
              <feOffset in="blur" dy="1.2" result="off" />
              <feComponentTransfer in="off" result="shadow">
                <feFuncA type="linear" slope="0.45" />
              </feComponentTransfer>
              <feMerge>
                <feMergeNode in="shadow" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <g filter={`url(#${filterId})`} className="analytics-donut-slices">
            {paths.map(({ d, fill, key }) => (
              <path
                key={key}
                d={d}
                fill={fill}
                className="analytics-donut-slice"
                stroke="rgba(15, 23, 42, 0.55)"
                strokeWidth="0.45"
                strokeLinejoin="round"
              />
            ))}
          </g>
        </svg>
        <div className="analytics-donut-hole analytics-donut-hole--raised">
          <span className="analytics-donut-total">{formatInt(total)}</span>
          <span className="analytics-donut-total-label">Total</span>
        </div>
      </div>
    </div>
  );
}

function PipelineLegend({ items = [], total }: { items?: AnalyticsNamedCount[]; total: number }) {
  if (total <= 0 || items.length === 0) {
    return <p className="analytics-chart-empty">No pipeline data yet.</p>;
  }
  return (
    <ul className="analytics-donut-legend">
      {items.map((row, i) => {
        const pct = total > 0 ? (100 * row.count) / total : 0;
        return (
          <li key={`${row.name}-${i}`} className="analytics-legend-row">
            <span className="analytics-legend-swatch" style={{ background: pipelineColor(row.name, i) }} />
            <span className="analytics-legend-label">{pipelineStatusLabel(row.name)}</span>
            <span className="analytics-legend-meta">
              {formatInt(row.count)}
              <span className="analytics-legend-pct">{pct.toFixed(1)}%</span>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function formatAvgSalary(n: number): string {
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0, minimumFractionDigits: 0 })}`;
}

function formatAvgYears(n: number): string {
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 1, minimumFractionDigits: 1 })} yrs`;
}

function filterOptionLabel(option: AnalyticsFilterOption): string {
  return option.label;
}

function countActiveFilters(filters: AnalyticsPageFilters): number {
  return Object.values(filters).filter(Boolean).length;
}

function AnalyticsFilterDropdown({
  label,
  value,
  allLabel,
  options,
  onChange,
}: {
  label: string;
  value: string;
  allLabel: string;
  options: AnalyticsFilterOption[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const labelId = useId().replace(/:/g, '');

  const selectedOption = options.find((option) => option.value === value);
  const displayLabel = selectedOption?.label ?? allLabel;

  useEffect(() => {
    if (!open) return undefined;

    const handlePointerDown = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const selectValue = (nextValue: string) => {
    onChange(nextValue);
    setOpen(false);
  };

  return (
    <label className="analytics-filter-field">
      <span id={labelId}>{label}</span>
      <div className="analytics-select-wrapper" ref={wrapperRef}>
        <button
          type="button"
          className={`analytics-select-trigger${open ? ' is-open' : ''}`}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-labelledby={labelId}
          onClick={() => setOpen((prev) => !prev)}
        >
          <span className="analytics-select-trigger-text">{displayLabel}</span>
          <span className={`analytics-select-chevron${open ? ' is-open' : ''}`} aria-hidden>
            ▼
          </span>
        </button>

        {open && (
          <ul className="analytics-select-menu" role="listbox" aria-labelledby={labelId}>
            <li role="presentation">
              <button
                type="button"
                role="option"
                aria-selected={value === ''}
                className={value === '' ? 'analytics-select-option is-selected' : 'analytics-select-option'}
                onClick={() => selectValue('')}
              >
                {allLabel}
              </button>
            </li>
            {options.map((option) => (
              <li key={`${label}-${option.value}`} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={value === option.value}
                  className={
                    value === option.value
                      ? 'analytics-select-option is-selected'
                      : 'analytics-select-option'
                  }
                  onClick={() => selectValue(option.value)}
                >
                  {filterOptionLabel(option)}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </label>
  );
}

function AverageByPositionBars({
  title,
  subtitle,
  items = [],
  accent,
  formatValue,
  valueHint,
  emptyMessage,
}: {
  title: string;
  subtitle?: string;
  items?: AnalyticsPositionAverage[];
  accent: 'amber' | 'sky';
  formatValue: (n: number) => string;
  valueHint: string;
  emptyMessage: string;
}) {
  const maxAvg = Math.max(1e-9, ...items.map((i) => i.average));
  return (
    <div className={`analytics-panel analytics-panel--vchart analytics-panel--accent-${accent}`}>
      <div className="analytics-panel-head">
        <h2>{title}</h2>
        {subtitle ? <p className="analytics-panel-sub">{subtitle}</p> : null}
      </div>
      {items.length === 0 ? (
        <p className="analytics-chart-empty">{emptyMessage}</p>
      ) : (
        <div className="analytics-vbar-chart" role="img" aria-label={title}>
          {items.map((row, idx) => {
            const pct = Math.min(100, (100 * row.average) / maxAvg);
            const tip = `${row.sample_count} candidate${row.sample_count === 1 ? '' : 's'} in average`;
            return (
              <div key={`${title}-${idx}-${row.name}`} className="analytics-vbar-col" title={tip}>
                <div className="analytics-vbar-value-top">{formatValue(row.average)}</div>
                <div className="analytics-vbar-bar-wrap">
                  <div
                    className="analytics-vbar-bar"
                    style={{ height: `${Math.max(pct, row.average > 0 ? 6 : 0)}%` }}
                  />
                </div>
                <div className="analytics-vbar-label" title={row.name}>
                  {row.name}
                </div>
                <div className="analytics-vbar-n">n={formatInt(row.sample_count)}</div>
              </div>
            );
          })}
        </div>
      )}
      {items.length > 0 && (
        <p className="analytics-metric-footnote">{valueHint}</p>
      )}
    </div>
  );
}

function BarList({
  title,
  subtitle,
  items = [],
  accent = 'purple',
}: {
  title: string;
  subtitle?: string;
  items?: AnalyticsNamedCount[];
  accent?: 'purple' | 'teal';
}) {
  const maxCount = Math.max(1, ...items.map((i) => i.count));
  return (
    <div className={`analytics-panel analytics-panel--bars analytics-panel--accent-${accent}`}>
      <div className="analytics-panel-head">
        <h2>{title}</h2>
        {subtitle ? <p className="analytics-panel-sub">{subtitle}</p> : null}
      </div>
      {items.length === 0 ? (
        <p className="analytics-chart-empty">No data in this category yet.</p>
      ) : (
        <div className="analytics-bar-list">
          {items.map((row, idx) => (
            <div key={`${title}-${idx}-${row.name}`} className="analytics-bar-row">
              <span className="analytics-bar-rank">{idx + 1}</span>
              <span className="analytics-bar-name" title={row.name}>
                {row.name}
              </span>
              <div className="analytics-bar-track">
                <div
                  className="analytics-bar-fill"
                  style={{ width: `${Math.min(100, (100 * row.count) / maxCount)}%` }}
                />
              </div>
              <span className="analytics-bar-count">{formatInt(row.count)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function KpiIconTotal() {
  return (
    <svg className="analytics-kpi-icon" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M12 4a4 4 0 100 8 4 4 0 000-8zM4 18c0-2.67 4-4 8-4s8 1.33 8 4v2H4v-2z"
        fill="currentColor"
        opacity="0.85"
      />
    </svg>
  );
}

function KpiIconCalendar() {
  return (
    <svg className="analytics-kpi-icon" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M7 2v2H5a2 2 0 00-2 2v12a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2h-2V2H7zm0 6h10v2H7V8zm0 4h6v2H7v-2z"
        fill="currentColor"
        opacity="0.85"
      />
    </svg>
  );
}

function KpiIconResume() {
  return (
    <svg className="analytics-kpi-icon" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm0 1.5L18.5 8H14V3.5zM8 12h8v1.5H8V12zm0 3h8V16.5H8V15z"
        fill="currentColor"
        opacity="0.85"
      />
    </svg>
  );
}

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [filters, setFilters] = useState<AnalyticsPageFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeFilterCount = countActiveFilters(filters);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const overview = await getAnalyticsOverview({
          status: filters.status || undefined,
          position: filters.position || undefined,
          location: filters.location || undefined,
        });
        if (!cancelled) setData(normalizeAnalyticsOverview(overview));
      } catch {
        if (!cancelled) {
          setError('Could not load analytics. Check your connection and try again.');
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const handleFilterChange = (key: keyof AnalyticsPageFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleClearFilters = () => {
    setFilters(EMPTY_FILTERS);
  };

  return (
    <div className="analytics-page">
      <div className="analytics-page-bg" aria-hidden />
      <header className="analytics-header">
        <span className="analytics-eyebrow">Insights</span>
        <h1>Analytics</h1>
        <p className="analytics-lead">
          Live summaries from your candidate pool.
        </p>
      </header>

      {data && (
        <section className="analytics-filters-section" aria-label="Analytics filters">
          <div className="analytics-filters-card">
            <div className="analytics-filters-head">
              <div>
                <h2>Filter analytics</h2>
                <p>Every KPI and chart below updates dynamically from the selected status, position, and location.</p>
              </div>
              <div className="analytics-filters-actions">
                {loading ? <span className="analytics-filters-status">Updating metrics…</span> : null}
                <button
                  type="button"
                  className="analytics-clear-btn"
                  onClick={handleClearFilters}
                  disabled={activeFilterCount === 0}
                >
                  Clear filters
                </button>
              </div>
            </div>

            <div className="analytics-filters-grid">
              <AnalyticsFilterDropdown
                label="Status"
                value={filters.status}
                allLabel="All statuses"
                options={data.filter_options.statuses}
                onChange={(value) => handleFilterChange('status', value)}
              />

              <AnalyticsFilterDropdown
                label="Position"
                value={filters.position}
                allLabel="All positions"
                options={data.filter_options.positions}
                onChange={(value) => handleFilterChange('position', value)}
              />

              <AnalyticsFilterDropdown
                label="Location"
                value={filters.location}
                allLabel="All locations"
                options={data.filter_options.locations}
                onChange={(value) => handleFilterChange('location', value)}
              />
            </div>

            <p className="analytics-filter-summary">
              {activeFilterCount > 0
                ? `${formatInt(data.total_candidates)} candidate${data.total_candidates === 1 ? '' : 's'} match the active filters.`
                : 'Showing the full organization candidate pool.'}
            </p>
          </div>
        </section>
      )}

      {error && <div className="analytics-error">{error}</div>}

      {loading && !data && (
        <div className="analytics-skeleton" aria-busy="true">
          <div className="analytics-skeleton-kpis" />
          <div className="analytics-skeleton-block" />
          <div className="analytics-skeleton-cols" />
        </div>
      )}

      {data && (
        <>
          <section className="analytics-kpi-grid" aria-label="Key metrics">
            <div className="analytics-kpi analytics-kpi--violet">
              <div className="analytics-kpi-top">
                <KpiIconTotal />
                <span className="analytics-kpi-label">Total candidates</span>
              </div>
              <div className="analytics-kpi-value">{formatInt(data.total_candidates)}</div>
            </div>
            <div className="analytics-kpi analytics-kpi--indigo">
              <div className="analytics-kpi-top">
                <KpiIconCalendar />
                <span className="analytics-kpi-label">New (30 days)</span>
              </div>
              <div className="analytics-kpi-value">{formatInt(data.recent_applications_30d)}</div>
              <div className="analytics-kpi-hint">Created in the last month</div>
            </div>
            <div className="analytics-kpi analytics-kpi--teal">
              <div className="analytics-kpi-top">
                <KpiIconResume />
                <span className="analytics-kpi-label">Resume on file</span>
              </div>
              <div className="analytics-kpi-value">{formatInt(data.candidates_with_resume)}</div>
              <div className="analytics-kpi-hint">{data.resume_coverage_percent}% of pool</div>
            </div>
          </section>

          <section className="analytics-pipeline-section" aria-labelledby="analytics-pipeline-heading">
            <div className="analytics-pipeline-card">
              <div className="analytics-pipeline-card-head">
                <h2 id="analytics-pipeline-heading">Pipeline status</h2>
                <span className="analytics-pipeline-badge">By HR status</span>
              </div>
              <p className="analytics-pipeline-intro">Share of candidates in each stage of your workflow.</p>
              <div className="analytics-pipeline-body">
                <PipelineDonut items={data.by_application_status} total={data.total_candidates} />
                <PipelineLegend items={data.by_application_status} total={data.total_candidates} />
              </div>
            </div>
          </section>

          <section className="analytics-columns analytics-columns--split" aria-label="Rankings">
            <BarList
              title="Top applied positions"
              subtitle="Most common role titles in your imports"
              items={data.top_applied_positions}
              accent="purple"
            />
            <BarList
              title="Top work locations"
              subtitle="Where candidates said they applied from"
              items={data.top_locations}
              accent="teal"
            />
          </section>

          <section className="analytics-vcharts-stack" aria-label="Averages by role">
            <AverageByPositionBars
              title="Avg expected salary by position"
              subtitle="Top roles by headcount — bar height is relative to the largest average in this chart"
              items={data.avg_expected_salary_by_position}
              accent="amber"
              formatValue={formatAvgSalary}
              emptyMessage="No candidates with both a role and at least one expected salary (remote or onsite) yet."
              valueHint="Per candidate we use remote expected salary if set, otherwise onsite."
            />
            <AverageByPositionBars
              title="Avg years of experience by position"
              subtitle="Among candidates who reported experience — bar height vs max average shown here"
              items={data.avg_years_experience_by_position}
              accent="sky"
              formatValue={formatAvgYears}
              emptyMessage="No candidates with both a role and years of experience filled in yet."
              valueHint="Average is taken over candidates with non-null experience for each position."
            />
          </section>
        </>
      )}
    </div>
  );
}
