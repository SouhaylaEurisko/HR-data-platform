  import { useMemo, useState } from 'react';
import type { AnalyzeResponse, ConfirmImportRequest } from '../types/api';
import { confirmImport } from '../api/import';
import type { ImportResult } from '../types/api';

interface Props {
  analysis: AnalyzeResponse;
  orgId: number;
  onComplete: (result: ImportResult) => void;
  onError: (message: string) => void;
  onCancel: () => void;
}

type Decision = 'map' | 'custom' | 'skip';

/** Select value for suggested/matched dropdown → store as new custom field on import */
const MAP_AS_CUSTOM_FIELD = '__custom_field__';

interface UnmatchedDecision {
  header: string;
  decision: Decision;
  targetColumn: string;
  customLabel: string;
}

export default function ColumnMappingReview({ analysis, orgId, onComplete, onError, onCancel }: Props) {
  const [matchedOverrides, setMatchedOverrides] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const col of analysis.matched_columns) {
      if (col.db_column) init[col.excel_header] = col.db_column;
    }
    return init;
  });

  const [suggestedOverrides, setSuggestedOverrides] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const col of analysis.suggested_columns) {
      if (col.db_column) init[col.excel_header] = col.db_column;
    }
    return init;
  });

  const [suggestedCustomLabels, setSuggestedCustomLabels] = useState<Record<string, string>>(() => {
    const init: Record<string, string> = {};
    for (const col of analysis.suggested_columns) {
      init[col.excel_header] = col.excel_header;
    }
    return init;
  });

  const [unmatchedDecisions, setUnmatchedDecisions] = useState<UnmatchedDecision[]>(
    analysis.unmatched_columns.map(col => ({
      header: col.excel_header,
      decision: 'custom' as Decision,
      targetColumn: '',
      customLabel: col.excel_header,
    }))
  );

  const [isSubmitting, setIsSubmitting] = useState(false);

  const allOptions = useMemo(() => {
    const byValue = new Map<string, { value: string; label: string }>();

    for (const col of analysis.available_columns) {
      if (!col?.value) continue;
      byValue.set(col.value, { value: col.value, label: col.label || col.value });
    }

    const ensureValue = (value?: string | null) => {
      if (!value || value === MAP_AS_CUSTOM_FIELD) return;
      if (!byValue.has(value)) {
        byValue.set(value, { value, label: value });
      }
    };

    for (const v of Object.values(matchedOverrides)) ensureValue(v);
    for (const v of Object.values(suggestedOverrides)) ensureValue(v);
    for (const ud of unmatchedDecisions) ensureValue(ud.targetColumn);

    return Array.from(byValue.values());
  }, [analysis.available_columns, matchedOverrides, suggestedOverrides, unmatchedDecisions]);

  const handleConfirm = async () => {
    setIsSubmitting(true);

    const confirmed: Record<string, string> = {};
    const newCustomFields: Array<{ header: string; label: string }> = [];
    const skipColumns: string[] = [];

    for (const col of analysis.matched_columns) {
      const override = matchedOverrides[col.excel_header];
      if (override) {
        confirmed[col.excel_header.toLowerCase()] = override;
      }
    }

    for (const col of analysis.suggested_columns) {
      const override = suggestedOverrides[col.excel_header];
      if (override === MAP_AS_CUSTOM_FIELD) {
        newCustomFields.push({
          header: col.excel_header,
          label: suggestedCustomLabels[col.excel_header]?.trim() || col.excel_header,
        });
      } else if (override) {
        confirmed[col.excel_header.toLowerCase()] = override;
      }
    }

    for (const ud of unmatchedDecisions) {
      if (ud.decision === 'skip') {
        skipColumns.push(ud.header);
      } else if (ud.decision === 'custom') {
        newCustomFields.push({ header: ud.header, label: ud.customLabel || ud.header });
      } else if (ud.decision === 'map' && ud.targetColumn) {
        confirmed[ud.header.toLowerCase()] = ud.targetColumn;
      }
    }

    const body: ConfirmImportRequest = {
      session_id: analysis.session_id,
      confirmed_mappings: confirmed,
      new_custom_fields: newCustomFields,
      skip_columns: skipColumns,
      sheet_names: analysis.sheets,
      org_id: orgId,
    };

    try {
      const result = await confirmImport(body);
      onComplete(result);
    } catch (err: any) {
      onError(err.response?.data?.detail || err.message || 'Import failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const totalMatched = analysis.matched_columns.length;
  const totalSuggested = analysis.suggested_columns.length;
  const totalUnmatched = unmatchedDecisions.length;
  const totalHeaders = totalMatched + totalSuggested + totalUnmatched;

  return (
    <div className="column-mapping-review">
      <h2>Review Column Mappings</h2>
      <p className="mapping-subtitle">
        File: <strong>{analysis.filename}</strong> &middot; Sheets: {analysis.sheets.join(', ')} &middot;{' '}
        <strong>{totalHeaders}</strong> columns detected
      </p>

      <div className="mapping-summary-bar">
        <span className="summary-chip chip-green">{totalMatched} matched</span>
        {totalSuggested > 0 && (
          <span className="summary-chip chip-yellow">{totalSuggested} need review</span>
        )}
        {totalUnmatched > 0 && (
          <span className="summary-chip chip-red">{totalUnmatched} unmatched</span>
        )}
      </div>

      {/* Auto-matched columns */}
      {analysis.matched_columns.length > 0 && (
        <section className="mapping-section mapping-matched">
          <h3>
            <span className="status-dot status-green" />
            Auto-Matched ({analysis.matched_columns.length})
          </h3>
          <p className="section-hint">These were matched automatically. You can change the mapping if needed.</p>
          <div className="mapping-table">
            {analysis.matched_columns.map((col, i) => (
              <div key={i} className="mapping-row">
                <span className="mapping-header">{col.excel_header}</span>
                <span className="mapping-arrow">&rarr;</span>
                <select
                  className="mapping-dropdown"
                  value={matchedOverrides[col.excel_header] || ''}
                  onChange={(e) =>
                    setMatchedOverrides(prev => ({
                      ...prev,
                      [col.excel_header]: e.target.value,
                    }))
                  }
                >
                  <option value="">-- Skip this column --</option>
                  {allOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <span className="mapping-badge badge-auto">
                  {col.source === 'programmatic' ? 'Exact Match' : `LLM ${Math.round(col.confidence * 100)}%`}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Suggested columns (LLM medium confidence) */}
      {analysis.suggested_columns.length > 0 && (
        <section className="mapping-section mapping-suggested">
          <h3>
            <span className="status-dot status-yellow" />
            Suggested Mappings ({analysis.suggested_columns.length})
          </h3>
          <p className="section-hint">
            The system thinks these might match. Please verify and adjust if needed.
          </p>
          <div className="mapping-table">
            {analysis.suggested_columns.map((col, i) => {
              const sel = suggestedOverrides[col.excel_header] || '';
              const isCustom = sel === MAP_AS_CUSTOM_FIELD;
              return (
                <div key={i} className="mapping-row mapping-row-suggested">
                  <span className="mapping-header">{col.excel_header}</span>
                  <span className="mapping-arrow">&rarr;</span>
                  <div className="unmatched-controls">
                    <select
                      className="mapping-dropdown"
                      value={isCustom ? MAP_AS_CUSTOM_FIELD : sel}
                      onChange={(e) => {
                        const v = e.target.value;
                        setSuggestedOverrides(prev => ({
                          ...prev,
                          [col.excel_header]: v,
                        }));
                        if (v === MAP_AS_CUSTOM_FIELD) {
                          setSuggestedCustomLabels(prev => ({
                            ...prev,
                            [col.excel_header]: prev[col.excel_header] || col.excel_header,
                          }));
                        }
                      }}
                    >
                      <option value="">-- Skip this column --</option>
                      <option value={MAP_AS_CUSTOM_FIELD}>Create custom field</option>
                      {allOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    {isCustom && (
                      <input
                        type="text"
                        className="mapping-input"
                        placeholder="Custom field label"
                        value={suggestedCustomLabels[col.excel_header] ?? ''}
                        onChange={(e) =>
                          setSuggestedCustomLabels(prev => ({
                            ...prev,
                            [col.excel_header]: e.target.value,
                          }))
                        }
                      />
                    )}
                  </div>
                  <span className="mapping-badge badge-suggested">
                    {Math.round(col.confidence * 100)}% confidence
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Unmatched columns */}
      {unmatchedDecisions.length > 0 && (
        <section className="mapping-section mapping-unmatched">
          <h3>
            <span className="status-dot status-red" />
            Unmatched Columns ({unmatchedDecisions.length})
          </h3>
          <p className="section-hint">
            No match found for these columns. Choose to map them to a database field, create a custom field, or skip.
          </p>
          <div className="mapping-table">
            {unmatchedDecisions.map((ud, i) => (
              <div key={i} className="mapping-row mapping-row-unmatched">
                <span className="mapping-header">{ud.header}</span>
                <span className="mapping-arrow">&rarr;</span>
                <div className="unmatched-controls">
                  <select
                    className="mapping-decision-select"
                    value={ud.decision}
                    onChange={(e) => {
                      const newDecisions = [...unmatchedDecisions];
                      newDecisions[i] = { ...ud, decision: e.target.value as Decision, targetColumn: '' };
                      setUnmatchedDecisions(newDecisions);
                    }}
                  >
                    <option value="map">Map to DB Field</option>
                    <option value="custom">Create Custom Field</option>
                    <option value="skip">Skip Column</option>
                  </select>

                  {ud.decision === 'map' && (
                    <select
                      className="mapping-dropdown"
                      value={ud.targetColumn}
                      onChange={(e) => {
                        const newDecisions = [...unmatchedDecisions];
                        newDecisions[i] = { ...ud, targetColumn: e.target.value };
                        setUnmatchedDecisions(newDecisions);
                      }}
                    >
                      <option value="">-- Select a field --</option>
                      {allOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  )}

                  {ud.decision === 'custom' && (
                    <input
                      type="text"
                      className="mapping-input"
                      placeholder="Custom field label"
                      value={ud.customLabel}
                      onChange={(e) => {
                        const newDecisions = [...unmatchedDecisions];
                        newDecisions[i] = { ...ud, customLabel: e.target.value };
                        setUnmatchedDecisions(newDecisions);
                      }}
                    />
                  )}

                  {ud.decision === 'skip' && (
                    <span className="skip-label">This column will be ignored</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="mapping-actions">
        <button className="btn-cancel" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </button>
        <button className="btn-confirm" onClick={handleConfirm} disabled={isSubmitting}>
          {isSubmitting ? 'Importing...' : 'Confirm and Import'}
        </button>
      </div>
    </div>
  );
}
