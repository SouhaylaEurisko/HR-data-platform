import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeXlsx, previewXlsx } from '../api/import';
import type { AnalyzeResponse, ImportResult, XlsxPreviewResponse } from '../types/api';
import ColumnMappingReview from '../components/ColumnMappingReview';
import './UploadPage.css';

type Phase = 'select' | 'analyzing' | 'review' | 'done';

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>('select');
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<XlsxPreviewResponse | null>(null);
  const [selectedSheets, setSelectedSheets] = useState<Set<string>>(new Set());
  const [importAll, setImportAll] = useState(false);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.toLowerCase().endsWith('.xlsx')) {
        setError('Please select an .xlsx file');
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError(null);
      setImportResult(null);
      setAnalysis(null);
      setPreview(null);
      setSelectedSheets(new Set());
      setImportAll(false);
      setPhase('select');

      setIsPreviewing(true);
      try {
        const previewData = await previewXlsx(selectedFile);
        setPreview(previewData);
        if (previewData.sheets.length === 1) {
          setSelectedSheets(new Set([previewData.sheets[0].name]));
        }
      } catch (err: any) {
        setError(
          err.response?.data?.detail ||
          err.message ||
          'Failed to preview file. You can still try to upload it.'
        );
      } finally {
        setIsPreviewing(false);
      }
    }
  };

  const handleSheetToggle = (sheetName: string) => {
    const newSelected = new Set(selectedSheets);
    if (newSelected.has(sheetName)) {
      newSelected.delete(sheetName);
    } else {
      newSelected.add(sheetName);
    }
    setSelectedSheets(newSelected);
    setImportAll(false);
  };

  const handleSelectAll = () => {
    if (preview) {
      setSelectedSheets(new Set(preview.sheets.map(s => s.name)));
      setImportAll(true);
    }
  };

  const handleDeselectAll = () => {
    setSelectedSheets(new Set());
    setImportAll(false);
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    if (preview && preview.sheets.length > 1) {
      if (!importAll && selectedSheets.size === 0) {
        setError('Please select at least one sheet to import, or choose "Import All Sheets"');
        return;
      }
    }

    setPhase('analyzing');
    setError(null);
    setAnalysis(null);

    try {
      const sheetNames = importAll ? undefined : Array.from(selectedSheets);
      const result = await analyzeXlsx(file, sheetNames, importAll);
      setAnalysis(result);
      setPhase('review');
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Failed to analyze file. Please try again.'
      );
      setPhase('select');
    }
  };

  const handleImportComplete = (result: ImportResult) => {
    setImportResult(result);
    setPhase('done');
    setFile(null);
    setPreview(null);
    setSelectedSheets(new Set());
    setImportAll(false);
    const fileInput = document.getElementById('file-input') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  const handleImportError = (message: string) => {
    setError(message);
  };

  const handleCancelReview = () => {
    setAnalysis(null);
    setPhase('select');
  };

  const handleNewUpload = () => {
    setPhase('select');
    setImportResult(null);
    setAnalysis(null);
    setError(null);
  };

  return (
    <div className="upload-page">
      <div className="page-top-bar">
        <div>
          <h1>Upload XLSX File</h1>
          <p className="upload-description">
            Upload an Excel file (.xlsx) to import candidate data. The system will
            analyze column headers and suggest mappings before importing.
          </p>
        </div>
        <button onClick={() => navigate('/candidates')} className="cross-nav-btn">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
          </svg>
          View Candidates
        </button>
      </div>

      {error && (
        <div className="error-message" role="alert">
          {error}
        </div>
      )}

      {/* Phase: Select file and sheets */}
      {(phase === 'select' || phase === 'analyzing') && (
        <form onSubmit={handleAnalyze} className="upload-form">
          <div className="file-input-wrapper">
            <label htmlFor="file-input" className="file-label">
              {file ? file.name : 'Choose XLSX file...'}
            </label>
            <input
              id="file-input"
              type="file"
              accept=".xlsx"
              onChange={handleFileChange}
              className="file-input"
              disabled={phase === 'analyzing'}
            />
          </div>

          {preview && preview.sheets.length > 1 && (
            <div className="sheet-selection">
              <div className="sheet-selection-header">
                <h3>Select Sheets to Import</h3>
                <div className="sheet-selection-actions">
                  <button
                    type="button"
                    onClick={handleSelectAll}
                    className="sheet-action-button"
                    disabled={phase === 'analyzing'}
                  >
                    Select All
                  </button>
                  <button
                    type="button"
                    onClick={handleDeselectAll}
                    className="sheet-action-button"
                    disabled={phase === 'analyzing'}
                  >
                    Deselect All
                  </button>
                </div>
              </div>
              <div className="sheets-list">
                {preview.sheets.map((sheet) => (
                  <label key={sheet.name} className="sheet-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedSheets.has(sheet.name) || importAll}
                      onChange={() => handleSheetToggle(sheet.name)}
                      disabled={phase === 'analyzing' || importAll}
                    />
                    <div className="sheet-info">
                      <span className="sheet-name">{sheet.name}</span>
                      <span className="sheet-details">
                        {sheet.data_rows} data row{sheet.data_rows !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
              <div className="import-all-option">
                <label className="import-all-checkbox">
                  <input
                    type="checkbox"
                    checked={importAll}
                    onChange={(e) => {
                      setImportAll(e.target.checked);
                      if (e.target.checked) handleSelectAll();
                    }}
                    disabled={phase === 'analyzing'}
                  />
                  <span>Import All Sheets ({preview.total_sheets} sheets)</span>
                </label>
              </div>
            </div>
          )}

          {isPreviewing && (
            <div className="preview-loading">Analyzing file structure...</div>
          )}

          {preview && preview.sheets.length === 1 && (
            <div className="single-sheet-notice">
              This file contains 1 sheet: <strong>{preview.sheets[0].name}</strong>
            </div>
          )}

          <button
            type="submit"
            disabled={!file || phase === 'analyzing' || isPreviewing}
            className="upload-button"
          >
            {phase === 'analyzing' ? 'Analyzing Columns...' : 'Analyze and Map Columns'}
          </button>
        </form>
      )}

      {/* Phase: Review column mappings */}
      {phase === 'review' && analysis && (
        <ColumnMappingReview
          analysis={analysis}
          orgId={1}
          onComplete={handleImportComplete}
          onError={handleImportError}
          onCancel={handleCancelReview}
        />
      )}

      {/* Phase: Done - show results */}
      {phase === 'done' && importResult && (
        <div className="upload-result">
          <h2>Import Summary</h2>
          <div className="result-stats">
            <div className="stat-item">
              <span className="stat-label">Session:</span>
              <span className="stat-value">#{importResult.session_id}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Status:</span>
              <span className="stat-value">{importResult.status}</span>
            </div>
            <div className="stat-item success">
              <span className="stat-label">Candidates Created:</span>
              <span className="stat-value">{importResult.total_created}</span>
            </div>
            {importResult.total_skipped_duplicates > 0 && (
              <div className="stat-item">
                <span className="stat-label">Duplicates Skipped:</span>
                <span className="stat-value">{importResult.total_skipped_duplicates}</span>
              </div>
            )}
            {importResult.total_errors > 0 && (
              <div className="stat-item">
                <span className="stat-label">Errors:</span>
                <span className="stat-value">{importResult.total_errors}</span>
              </div>
            )}
          </div>

          {importResult.sheet_results && importResult.sheet_results.length > 0 && (
            <div className="sheet-results">
              <h3>Per-Sheet Results:</h3>
              {importResult.sheet_results.map((sr, idx) => (
                <div key={idx} className="sheet-result-card">
                  <h4>{sr.sheet_name}</h4>
                  <div className="sheet-stats">
                    <span className="sheet-stat">
                      Created: <strong>{sr.created}</strong>
                    </span>
                    {sr.skipped_duplicates > 0 && (
                      <span className="sheet-stat">
                        Duplicates: <strong>{sr.skipped_duplicates}</strong>
                      </span>
                    )}
                  </div>
                  {sr.row_errors.length > 0 && (
                    <div className="sheet-errors">
                      <strong>Errors ({sr.row_errors.length}):</strong>
                      <ul>
                        {sr.row_errors.slice(0, 5).map((err, errIdx) => (
                          <li key={errIdx}>Row {err.row_index}: {err.error}</li>
                        ))}
                        {sr.row_errors.length > 5 && (
                          <li>... and {sr.row_errors.length - 5} more errors</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {importResult.row_errors && importResult.row_errors.length > 0 && (
            <div className="error-details">
              <h3>Row Errors:</h3>
              <ul>
                {importResult.row_errors.slice(0, 10).map((err, idx) => (
                  <li key={idx}>
                    {err.sheet ? `${err.sheet} - ` : ''}Row {err.row_index}: {err.error}
                  </li>
                ))}
                {importResult.row_errors.length > 10 && (
                  <li>... and {importResult.row_errors.length - 10} more errors</li>
                )}
              </ul>
            </div>
          )}

          {importResult.total_created > 0 && (
            <div className="success-message">
              Successfully imported {importResult.total_created} candidate(s)!
            </div>
          )}

          <button className="upload-button" onClick={handleNewUpload}>
            Upload Another File
          </button>
        </div>
      )}
    </div>
  );
}
