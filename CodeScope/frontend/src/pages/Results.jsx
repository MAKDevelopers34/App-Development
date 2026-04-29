import { useLocation, useNavigate } from 'react-router-dom';
import RatingGauge from '../components/RatingGauge';
import ComplexityBadge from '../components/ComplexityBadge';
import IssueCard from '../components/IssueCard';
import { downloadReport } from '../services/api';
import { useState } from 'react';

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  const [downloading, setDownloading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(0);

  // Safe state extraction
  const stateData = location.state || {};
  const result = stateData.result;
  const type = stateData.type;

  const getSafeFilename = (data, fallback = 'Unknown File') => {
    const filename = data?.filename || data?.result?.filename || fallback;
    return typeof filename === 'string' && filename.trim() ? filename : fallback;
  };

  if (!result) {
    navigate('/analyze');
    return null;
  }

  const handleDownload = async () => {
    setDownloading(true);
    try {
      if (!result || !type) {
        alert('No result data available. Please analyze code first.');
        return;
      }

      const reportData = type === 'code'
        ? { ...result, filename: getSafeFilename(result) }
        : {
            ...result,
            files: Array.isArray(result?.files)
              ? result.files.map((file, index) => ({
                  ...file,
                  filename: getSafeFilename(file, `File ${index + 1}`),
                }))
              : [],
          };

      await downloadReport(reportData, type);
    } catch (err) {
      console.error("Download error:", err);
      alert('PDF download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  // Single file result - FIXED with safe access
  const renderSingleResult = (data, filename) => {
    const r = data?.result || data || {};

    // Safe defaults for missing properties
    const rating = r?.rating || 0;
    const time_complexity = r?.time_complexity || 'Unknown';
    const space_complexity = r?.space_complexity || 'Unknown';
    const language = r?.language || 'Unknown';
    const lines_of_code = r?.lines_of_code || 0;
    const issues = Array.isArray(r?.issues) ? r.issues : [];
    const suggestions = Array.isArray(r?.suggestions) ? r.suggestions : [];
    const safeFilename = filename || getSafeFilename(data);

    return (
      <div data-filename={safeFilename}>
        {/* Metrics row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          {/* Rating */}
          <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Performance Rating
            </div>
            <RatingGauge rating={rating} />
          </div>

          {/* Time Complexity */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Time Complexity
            </div>
            <ComplexityBadge complexity={time_complexity} />
            <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '10px', lineHeight: '1.5' }}>
              How execution time grows as input size increases
            </div>
          </div>

          {/* Space Complexity */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Space Complexity
            </div>
            <ComplexityBadge complexity={space_complexity} />
            <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '10px', lineHeight: '1.5' }}>
              How memory usage grows as input size increases
            </div>
          </div>

          {/* Stats */}
          <div className="card" style={{ padding: '24px' }}>
            <div style={{ fontSize: '13px', color: 'var(--gray)', marginBottom: '12px', fontWeight: '500' }}>
              Code Stats
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--gray)' }}>Language</span>
                <span style={{ fontSize: '13px', fontWeight: '600', textTransform: 'uppercase' }}>
                  {language.toUpperCase()}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--gray)' }}>Lines of Code</span>
                <span style={{ fontSize: '13px', fontWeight: '600' }}>{lines_of_code}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '13px', color: 'var(--gray)' }}>Issues Found</span>
                <span style={{ fontSize: '13px', fontWeight: '600', color: issues.length > 0 ? 'var(--danger)' : 'var(--success)' }}>
                  {issues.length}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Issues */}
        {issues.length > 0 && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
              ⚠️ Issues Found ({issues.length})
            </h3>
            {issues.map((issue, i) => (
              <IssueCard key={i} issue={issue} />
            ))}
          </div>
        )}

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div className="card" style={{ marginBottom: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px' }}>
              💡 Optimization Suggestions
            </h3>
            {suggestions.map((suggestion, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                padding: '12px 0',
                borderBottom: i < suggestions.length - 1 ? '1px solid var(--border)' : 'none'
              }}>
                <div style={{
                  width: '24px', height: '24px',
                  background: 'var(--primary-light)',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: '700',
                  color: 'var(--primary)',
                  flexShrink: 0
                }}>
                  {i + 1}
                </div>
                <p style={{ fontSize: '14px', color: 'var(--dark)', lineHeight: '1.6', margin: 0 }}>
                  {suggestion || 'No suggestion available'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Multi file result - FIXED with safe access
  const renderMultiResult = () => {
    const files = Array.isArray(result?.files) ? result.files : [];

    return (
      <div>
        {/* Summary cards */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          {[
            { label: 'Total Files', value: result?.total_files || 0, icon: '📁' },
            { label: 'Total Lines', value: result?.total_lines || 0, icon: '📝' },
            { label: 'Total Issues', value: result?.total_issues || 0, icon: '⚠️' },
            { label: 'Avg Rating', value: `${(result?.average_rating || 0).toFixed(1)}/10`, icon: '⭐' },
          ].map(({ label, value, icon }) => (
            <div key={label} className="card" style={{ textAlign: 'center', padding: '20px' }}>
              <div style={{ fontSize: '24px', marginBottom: '8px' }}>{icon}</div>
              <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--primary)' }}>{value}</div>
              <div style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '4px' }}>{label}</div>
            </div>
          ))}
        </div>

        {/* File selector */}
        <div className="card" style={{ marginBottom: '20px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '14px' }}>
            📂 Files Analyzed ({files.length})
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
            {files.map((file, i) => (
              <button
                key={i}
                onClick={() => setSelectedFile(i)}
                style={{
                  padding: '6px 14px',
                  borderRadius: '8px',
                  border: '1.5px solid',
                  borderColor: selectedFile === i ? 'var(--primary)' : 'var(--border)',
                  background: selectedFile === i ? 'var(--primary-light)' : 'white',
                  color: selectedFile === i ? 'var(--primary)' : 'var(--gray)',
                  fontSize: '12px',
                  fontWeight: '500',
                  cursor: 'pointer',
                  fontFamily: 'var(--font-code)'
                }}
              >
                {getSafeFilename(file, `File ${i + 1}`).split('/').pop()}
              </button>
            ))}
          </div>

          {/* Selected file result */}
          {files[selectedFile] && renderSingleResult(files[selectedFile], files[selectedFile]?.filename)}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: '48px 0', minHeight: '80vh' }}>
      <div className="container">
        {/* Header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '32px',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div>
            <h1 style={{ fontSize: '28px', fontWeight: '700', marginBottom: '4px' }}>
              Analysis Results
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--gray)' }}>
              {type === 'code' && `File: ${result?.filename || 'Unknown'}`}
              {type === 'zip' && `ZIP file — ${result?.total_files || 0} files analyzed`}
              {type === 'github' && `GitHub: ${result?.github_url || 'Unknown'}`}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={() => navigate('/analyze')}
              className="btn btn-outline"
            >
              ← Analyze Another
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="btn btn-primary"
            >
              {downloading ? '⏳ Generating...' : '📄 Download PDF'}
            </button>
          </div>
        </div>

        {/* Results */}
        {type === 'code' && renderSingleResult(result, result?.filename)}
        {(type === 'zip' || type === 'github') && renderMultiResult()}
      </div>
    </div>
  );
}
