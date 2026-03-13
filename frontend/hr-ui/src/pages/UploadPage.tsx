import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { importXlsx, previewXlsx } from '../api/import';
import type { ImportXlsxResponse, XlsxPreviewResponse } from '../types/api';
import './UploadPage.css';

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [result, setResult] = useState<ImportXlsxResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<XlsxPreviewResponse | null>(null);
  const [selectedSheets, setSelectedSheets] = useState<Set<string>>(new Set());
  const [importAll, setImportAll] = useState(false);

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
      setResult(null);
      setPreview(null);
      setSelectedSheets(new Set());
      setImportAll(false);

      // Preview the file to get sheet information
      setIsPreviewing(true);
      try {
        const previewData = await previewXlsx(selectedFile);
        setPreview(previewData);
        // If only one sheet, select it by default
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    // If we have preview and sheets, validate selection
    if (preview && preview.sheets.length > 1) {
      if (!importAll && selectedSheets.size === 0) {
        setError('Please select at least one sheet to import, or choose "Import All Sheets"');
        return;
      }
    }

    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const sheetNames = importAll ? undefined : Array.from(selectedSheets);
      const response = await importXlsx(file, sheetNames, importAll);
      setResult(response);
      setFile(null);
      setPreview(null);
      setSelectedSheets(new Set());
      setImportAll(false);
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        err.message || 
        'Failed to upload file. Please try again.'
      );
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="page-top-bar">
        <div>
          <h1>Upload XLSX File</h1>
          <p className="upload-description">
            Upload an Excel file (.xlsx) to import candidate data into the system.
          </p>
        </div>
        <button onClick={() => navigate('/candidates')} className="cross-nav-btn">
          <svg viewBox="0 0 20 20" fill="currentColor">
            <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
          </svg>
          View Candidates
        </button>
      </div>

      <form onSubmit={handleSubmit} className="upload-form">
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
            disabled={isUploading}
          />
        </div>

        {error && (
          <div className="error-message" role="alert">
            {error}
          </div>
        )}

        {/* Sheet Selection */}
        {preview && preview.sheets.length > 1 && (
          <div className="sheet-selection">
            <div className="sheet-selection-header">
              <h3>Select Sheets to Import</h3>
              <div className="sheet-selection-actions">
                <button
                  type="button"
                  onClick={handleSelectAll}
                  className="sheet-action-button"
                  disabled={isUploading}
                >
                  Select All
                </button>
                <button
                  type="button"
                  onClick={handleDeselectAll}
                  className="sheet-action-button"
                  disabled={isUploading}
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
                    disabled={isUploading || importAll}
                  />
                  <div className="sheet-info">
                    <span className="sheet-name">
                      {sheet.name}
                    </span>
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
                    if (e.target.checked) {
                      handleSelectAll();
                    }
                  }}
                  disabled={isUploading}
                />
                <span>Import All Sheets ({preview.total_sheets} sheets)</span>
              </label>
            </div>
          </div>
        )}

        {isPreviewing && (
          <div className="preview-loading">
            Analyzing file structure...
          </div>
        )}

        {preview && preview.sheets.length === 1 && (
          <div className="single-sheet-notice">
            This file contains 1 sheet: <strong>{preview.sheets[0].name}</strong>
          </div>
        )}

        <button
          type="submit"
          disabled={!file || isUploading || isPreviewing}
          className="upload-button"
        >
          {isUploading ? 'Uploading...' : 'Upload File'}
        </button>
      </form>

      {result && (
        <div className="upload-result">
          <h2>Upload Summary</h2>
          <div className="result-stats">
            <div className="stat-item">
              <span className="stat-label">File Name:</span>
              <span className="stat-value">{result.file_name}</span>
            </div>
            
            {/* Multi-sheet results */}
            {result.sheets_processed && result.sheets_processed.length > 0 && (
              <>
                <div className="stat-item">
                  <span className="stat-label">Sheets Processed:</span>
                  <span className="stat-value">{result.sheets_processed.join(', ')}</span>
                </div>
                <div className="stat-item success">
                  <span className="stat-label">Total Candidates Created:</span>
                  <span className="stat-value">{result.total_created ?? 0}</span>
                </div>
                {result.total_skipped_duplicates && result.total_skipped_duplicates > 0 && (
                  <div className="stat-item">
                    <span className="stat-label">Total Duplicates Skipped:</span>
                    <span className="stat-value">{result.total_skipped_duplicates}</span>
                  </div>
                )}
              </>
            )}
            
            {/* Legacy single-sheet results (backward compatibility) */}
            {!result.sheets_processed && (
              <>
                <div className="stat-item success">
                  <span className="stat-label">Candidates Created:</span>
                  <span className="stat-value">{result.created ?? 0}</span>
                </div>
                {result.skipped_duplicates && result.skipped_duplicates > 0 && (
                  <div className="stat-item">
                    <span className="stat-label">Duplicates Skipped:</span>
                    <span className="stat-value">{result.skipped_duplicates}</span>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Per-sheet breakdown */}
          {result.sheet_results && result.sheet_results.length > 0 && (
            <div className="sheet-results">
              <h3>Per-Sheet Results:</h3>
              {result.sheet_results.map((sheetResult, idx) => (
                <div key={idx} className="sheet-result-card">
                  <h4>{sheetResult.sheet_name}</h4>
                  <div className="sheet-stats">
                    <span className="sheet-stat">
                      Created: <strong>{sheetResult.created}</strong>
                    </span>
                    {sheetResult.skipped_duplicates > 0 && (
                      <span className="sheet-stat">
                        Duplicates: <strong>{sheetResult.skipped_duplicates}</strong>
                      </span>
                    )}
                    {sheetResult.skipped_empty_rows > 0 && (
                      <span className="sheet-stat">
                        Empty Rows: <strong>{sheetResult.skipped_empty_rows}</strong>
                      </span>
                    )}
                  </div>
                  {sheetResult.row_errors.length > 0 && (
                    <div className="sheet-errors">
                      <strong>Errors ({sheetResult.row_errors.length}):</strong>
                      <ul>
                        {sheetResult.row_errors.slice(0, 5).map((err, errIdx) => (
                          <li key={errIdx}>
                            Row {err.row_index}: {err.error}
                          </li>
                        ))}
                        {sheetResult.row_errors.length > 5 && (
                          <li>... and {sheetResult.row_errors.length - 5} more errors</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Legacy row errors (backward compatibility) */}
          {result.row_errors && result.row_errors.length > 0 && (
            <div className="error-details">
              <h3>Row Errors:</h3>
              <ul>
                {result.row_errors.slice(0, 10).map((err, idx) => (
                  <li key={idx}>
                    {err.sheet ? `${err.sheet} - ` : ''}Row {err.row_index}: {err.error}
                  </li>
                ))}
                {result.row_errors.length > 10 && (
                  <li>... and {result.row_errors.length - 10} more errors</li>
                )}
              </ul>
            </div>
          )}

          {(result.total_created ?? result.created ?? 0) > 0 && (
            <div className="success-message">
              ✓ Successfully imported {result.total_created ?? result.created ?? 0} candidate(s)!
            </div>
          )}
        </div>
      )}
    </div>
  );
}