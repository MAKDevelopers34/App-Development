import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { analyzeCode, analyzeZip, analyzeGithub } from '../services/api';

export default function Analyze() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('code');
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('code.py');
  const [githubUrl, setGithubUrl] = useState('');
  const [zipFile, setZipFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/zip': ['.zip'] },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      setZipFile(acceptedFiles[0]);
      setError('');
    }
  });

  const handleAnalyze = async () => {
    setError('');
    setLoading(true);

    try {
      let result;

      if (activeTab === 'code') {
        if (!code.trim()) {
          setError('Please enter some code to analyze.');
          setLoading(false);
          return;
        }
        result = await analyzeCode(code, filename);
        navigate('/results', { state: { result, type: 'code' } });

      } else if (activeTab === 'zip') {
        if (!zipFile) {
          setError('Please upload a ZIP file.');
          setLoading(false);
          return;
        }
        result = await analyzeZip(zipFile);
        navigate('/results', { state: { result, type: 'zip' } });

      } else if (activeTab === 'github') {
        if (!githubUrl.trim()) {
          setError('Please enter a GitHub URL.');
          setLoading(false);
          return;
        }
        result = await analyzeGithub(githubUrl);
        navigate('/results', { state: { result, type: 'github' } });
      }

    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const tabStyle = (tab) => ({
    padding: '10px 24px',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    fontFamily: 'var(--font)',
    transition: 'all 0.2s',
    background: activeTab === tab ? 'var(--primary)' : 'transparent',
    color: activeTab === tab ? 'white' : 'var(--gray)',
  });

  return (
    <div style={{ padding: '48px 0', minHeight: '80vh' }}>
      <div className="container" style={{ maxWidth: '800px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 className="section-title">Analyze Your Code</h1>
          <p className="section-subtitle">
            Choose how you want to upload your code below
          </p>
        </div>

        {/* Main card */}
        <div className="card" style={{ padding: '32px' }}>

          {/* Tabs */}
          <div style={{
            display: 'flex',
            gap: '4px',
            background: 'var(--light-gray)',
            padding: '4px',
            borderRadius: '10px',
            marginBottom: '28px'
          }}>
            {[
              { key: 'code', label: '📝 Paste Code' },
              { key: 'zip', label: '📁 Upload ZIP' },
              { key: 'github', label: '🔗 GitHub URL' },
            ].map(({ key, label }) => (
              <button
                key={key}
                style={tabStyle(key)}
                onClick={() => { setActiveTab(key); setError(''); }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab: Paste Code */}
          {activeTab === 'code' && (
            <div>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '13px', fontWeight: '500', color: 'var(--dark)', display: 'block', marginBottom: '6px' }}>
                  Filename (helps detect language)
                </label>
                <input
                  type="text"
                  value={filename}
                  onChange={e => setFilename(e.target.value)}
                  placeholder="e.g. main.py, index.js, Solution.java"
                  style={{ marginBottom: '0' }}
                />
              </div>
              <div>
                <label style={{ fontSize: '13px', fontWeight: '500', color: 'var(--dark)', display: 'block', marginBottom: '6px' }}>
                  Paste your code here
                </label>
                <textarea
                  value={code}
                  onChange={e => setCode(e.target.value)}
                  placeholder={`# Paste your code here\ndef example(arr):\n    for i in range(len(arr)):\n        for j in range(len(arr)):\n            print(arr[i], arr[j])`}
                  rows={14}
                  style={{
                    fontFamily: 'var(--font-code)',
                    fontSize: '13px',
                    resize: 'vertical',
                    lineHeight: '1.6'
                  }}
                />
              </div>
            </div>
          )}

          {/* Tab: Upload ZIP */}
          {activeTab === 'zip' && (
            <div>
              <div
                {...getRootProps()}
                style={{
                  border: `2px dashed ${isDragActive ? 'var(--primary)' : 'var(--border)'}`,
                  borderRadius: '12px',
                  padding: '48px 24px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: isDragActive ? 'var(--primary-light)' : 'var(--light-gray)',
                  transition: 'all 0.2s'
                }}
              >
                <input {...getInputProps()} />
                <div style={{ fontSize: '40px', marginBottom: '12px' }}>📁</div>
                {zipFile ? (
                  <div>
                    <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--primary)', marginBottom: '4px' }}>
                      ✅ {zipFile.name}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--gray)' }}>
                      {(zipFile.size / 1024).toFixed(1)} KB — Click to change
                    </div>
                  </div>
                ) : (
                  <div>
                    <div style={{ fontSize: '15px', fontWeight: '600', marginBottom: '4px' }}>
                      {isDragActive ? 'Drop your ZIP file here' : 'Drag & drop your ZIP file here'}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--gray)' }}>
                      or click to browse — supports .zip files only
                    </div>
                  </div>
                )}
              </div>
              <p style={{ fontSize: '12px', color: 'var(--gray)', marginTop: '10px' }}>
                💡 Tip: ZIP your project folder and upload. We'll analyze all Python, JavaScript, Java, C++, and TypeScript files inside.
              </p>
            </div>
          )}

          {/* Tab: GitHub URL */}
          {activeTab === 'github' && (
            <div>
              <label style={{ fontSize: '13px', fontWeight: '500', color: 'var(--dark)', display: 'block', marginBottom: '6px' }}>
                GitHub Repository URL
              </label>
              <input
                type="text"
                value={githubUrl}
                onChange={e => setGithubUrl(e.target.value)}
                placeholder="https://github.com/username/repository"
                style={{ marginBottom: '10px', fontSize: '14px' }}
              />
              <p style={{ fontSize: '12px', color: 'var(--gray)' }}>
                💡 Tip: Make sure the repository is public. We'll fetch and analyze up to 20 code files automatically.
              </p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="error-box" style={{ marginTop: '16px' }}>
              ⚠️ {error}
            </div>
          )}

          {/* Analyze Button */}
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="btn btn-primary"
            style={{
              width: '100%',
              justifyContent: 'center',
              padding: '14px',
              fontSize: '16px',
              fontWeight: '600',
              marginTop: '24px',
              opacity: loading ? 0.7 : 1,
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? (
              <>
                <div className="spinner" style={{ width: '18px', height: '18px' }}></div>
                Analyzing...
              </>
            ) : (
              '🔍 Analyze Now'
            )}
          </button>

        </div>
      </div>
    </div>
  );
}