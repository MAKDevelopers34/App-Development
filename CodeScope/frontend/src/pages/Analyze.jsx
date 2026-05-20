import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { analyzeCode, analyzeZip, analyzeGithub, getApiErrorMessage, inferInputs } from '../services/api';

const splitParams = (raw = '') => {
  const params = [];
  let current = '';
  let depth = 0;
  const openers = new Set(['<', '[', '(', '{']);
  const closers = new Set(['>', ']', ')', '}']);

  for (const ch of raw) {
    if (openers.has(ch)) depth += 1;
    if (closers.has(ch) && depth > 0) depth -= 1;
    if (ch === ',' && depth === 0) {
      params.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  if (current.trim()) params.push(current.trim());
  return params;
};

const languageFromFilename = (filename = '') => {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (['ts', 'tsx', 'mts', 'cts'].includes(ext)) return 'typescript';
  if (['js', 'jsx', 'mjs', 'cjs'].includes(ext)) return 'javascript';
  if (ext === 'java') return 'java';
  if (['cpp', 'cc', 'cxx', 'c++', 'hpp', 'hh', 'hxx', 'ipp', 'h', 'c'].includes(ext)) return 'cpp';
  return 'python';
};

const inferKind = (name, declaredType = '') => {
  const text = `${declaredType} ${name}`.toLowerCase();
  if (/(bool|boolean|flag|is_|has_|can_)/.test(text)) return { kind: 'boolean', placeholder: 'true' };
  if (/(list|array|vector|\[\]|tuple|set)/.test(text) || /^(arr|nums|numbers|items|values|visited|seen)$/i.test(name)) {
    return { kind: 'array', placeholder: '[1, 2, 3]' };
  }
  if (/(dict|map|object|graph|adj)/.test(text)) return { kind: 'object', placeholder: '{"a": [1, 2]}' };
  if (/(str|string|char)/.test(text) || /^(s|text|word|pattern)$/i.test(name)) return { kind: 'string', placeholder: 'hello' };
  if (/(float|double|decimal)/.test(text)) return { kind: 'number', placeholder: '3.14' };
  if (/(int|long|size_t|short)/.test(text) || /^(n|m|k|i|j|target|size|length|count|limit)$/i.test(name)) {
    return { kind: 'integer', placeholder: '10' };
  }
  return { kind: 'string', placeholder: 'value' };
};

const parseParam = (raw, language) => {
  const cleaned = raw.replace(/=.*/, '').trim();
  if (!cleaned) return null;

  if (language === 'python') {
    const [namePart, declaredType = ''] = cleaned.split(':').map(part => part.trim());
    const name = namePart.replace(/^\*+/, '');
    if (!name || ['self', 'cls'].includes(name)) return null;
    return { name, declaredType };
  }

  if (language === 'typescript') {
    const [namePart, ...typeParts] = cleaned.split(':');
    const name = namePart.trim().replace(/^[.]+/, '');
    const declaredType = typeParts.join(':').trim();
    if (!name) return null;
    return { name, declaredType };
  }

  const arrayMatch = cleaned.match(/(\w+)\s*\[\s*\]$/);
  if (arrayMatch) {
    return {
      name: arrayMatch[1],
      declaredType: `${cleaned.slice(0, arrayMatch.index).trim()}[]`,
    };
  }

  const tokens = cleaned.replace(/[&*]/g, ' ').trim().split(/\s+/);
  const name = tokens[tokens.length - 1];
  if (!name) return null;
  return {
    name,
    declaredType: tokens.length > 1 ? cleaned.slice(0, cleaned.lastIndexOf(name)).trim() : '',
  };
};

const inferInputSchema = (code, filename) => {
  const language = languageFromFilename(filename);
  const patterns = language === 'python'
    ? [/def\s+(\w+)\s*\(([^)]*)\)/]
    : ['javascript', 'typescript'].includes(language)
      ? [
          /function\s*\*?\s+(\w+)\s*\(([^)]*)\)\s*(?::\s*[^={]+)?/,
          /(?:const|let|var)\s+(\w+)\s*=\s*\(([^)]*)\)\s*(?::\s*[^=]+)?=>/,
          /(?:const|let|var)\s+(\w+)\s*=\s*([A-Za-z_]\w*(?:\s*:\s*[^=]+)?)\s*=>/,
        ]
      : [/(?:public|private|protected)?\s*(?:static\s+)?[\w:<>\][, ?&*]+\s+(\w+)\s*\(([^)]*)\)/];

  for (const pattern of patterns) {
    const match = code.match(pattern);
    if (!match) continue;
    const params = splitParams(match[2])
      .map(raw => parseParam(raw, language))
      .filter(Boolean)
      .map(param => ({ ...param, ...inferKind(param.name, param.declaredType) }));

    if (params.length) {
      return { available: true, function: match[1], language, parameters: params };
    }
  }
  return { available: false, function: null, language, parameters: [] };
};

const parseInputValue = (value, kind) => {
  const text = String(value ?? '').trim();
  if (!text) return undefined;
  if (kind === 'integer') return Number.parseInt(text, 10);
  if (kind === 'number') return Number.parseFloat(text);
  if (kind === 'boolean') return /^(true|1|yes)$/i.test(text);
  if (kind === 'array' || kind === 'object') {
    try { return JSON.parse(text); } catch { return text; }
  }
  return text;
};

const buildConcreteInputPayload = (schema, values, fallbackText) => {
  if (schema?.available) {
    const payload = {};
    schema.parameters.forEach(param => {
      const parsed = parseInputValue(values[param.name], param.kind);
      if (parsed !== undefined && !(typeof parsed === 'number' && Number.isNaN(parsed))) {
        payload[param.name] = parsed;
      }
    });
    if (Object.keys(payload).length) return payload;
  }
  return fallbackText;
};

export default function Analyze() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('code');
  const [code, setCode] = useState('');
  const [filename, setFilename] = useState('code.py');
  const [concreteInputs, setConcreteInputs] = useState('');
  const [inputValues, setInputValues] = useState({});
  const [githubUrl, setGithubUrl] = useState('');
  const [zipFile, setZipFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [backendInputSchema, setBackendInputSchema] = useState(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const localInputSchema = useMemo(() => inferInputSchema(code, filename), [code, filename]);
  const inputSchema = backendInputSchema || localInputSchema;

  useEffect(() => {
    const trimmed = code.trim();
    if (!trimmed) {
      return undefined;
    }

    let active = true;
    const timer = window.setTimeout(async () => {
      if (active) setSchemaLoading(true);
      try {
        const response = await inferInputs(code, filename);
        if (active && response?.input_schema) {
          setBackendInputSchema(response.input_schema);
        }
      } catch {
        if (active) setBackendInputSchema(null);
      } finally {
        if (active) setSchemaLoading(false);
      }
    }, 350);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [code, filename]);

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
        result = await analyzeCode(
          code,
          filename,
          buildConcreteInputPayload(inputSchema, inputValues, concreteInputs)
        );
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
      setError(getApiErrorMessage(err));
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
                  onChange={e => {
                    setFilename(e.target.value);
                    setBackendInputSchema(null);
                    setSchemaLoading(Boolean(code.trim()));
                  }}
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
                  onChange={e => {
                    const nextCode = e.target.value;
                    setCode(nextCode);
                    setBackendInputSchema(null);
                    setSchemaLoading(Boolean(nextCode.trim()));
                  }}
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
              {inputSchema.available ? (
                <div style={{ marginTop: '16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <label style={{ fontSize: '13px', fontWeight: '600', color: 'var(--dark)' }}>
                      Inputs for {inputSchema.function}()
                    </label>
                    <span style={{ fontSize: '12px', color: 'var(--gray)', fontFamily: 'var(--font-code)' }}>
                      {schemaLoading ? 'Checking analyzer' : backendInputSchema ? 'Analyzer schema' : 'Detected from pasted code'}
                    </span>
                  </div>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '12px'
                  }}>
                    {inputSchema.parameters.map(param => (
                      <div key={param.name}>
                        <label style={{ fontSize: '12px', fontWeight: '600', color: 'var(--dark)', display: 'block', marginBottom: '5px', fontFamily: 'var(--font-code)' }}>
                          {param.name}
                          <span style={{ color: 'var(--gray)', fontFamily: 'var(--font)', fontWeight: '500' }}>
                            {' '}({param.kind})
                          </span>
                        </label>
                        <input
                          type={param.kind === 'integer' || param.kind === 'number' ? 'number' : 'text'}
                          value={inputValues[param.name] || ''}
                          onChange={e => setInputValues(prev => ({ ...prev, [param.name]: e.target.value }))}
                          placeholder={param.placeholder}
                          style={{ marginBottom: 0, fontFamily: 'var(--font-code)', fontSize: '13px' }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div style={{ marginTop: '16px' }}>
                  <label style={{ fontSize: '13px', fontWeight: '500', color: 'var(--dark)', display: 'block', marginBottom: '6px' }}>
                    Input values (optional)
                  </label>
                  <input
                    type="text"
                    value={concreteInputs}
                    onChange={e => setConcreteInputs(e.target.value)}
                    placeholder="m=2, n=2 or functionName(2, 2)"
                    style={{ marginBottom: '0', fontFamily: 'var(--font-code)', fontSize: '13px' }}
                  />
                </div>
              )}
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
