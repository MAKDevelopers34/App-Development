import axios from 'axios';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
).replace(/\/+$/, '');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

export const getApiErrorMessage = (error, fallback = 'Request failed. Please try again.') => (
  error?.response?.data?.error ||
  error?.response?.data?.message ||
  error?.message ||
  fallback
);

const sleep = (ms) => new Promise(resolve => window.setTimeout(resolve, ms));

export const analyzeCode = async (code, filename = 'code.py', concreteInputs = '') => {
  const payload = { code, filename };

  if (concreteInputs) {
    if (typeof concreteInputs === 'string') {
      if (concreteInputs.trim()) payload.concrete_inputs = concreteInputs.trim();
    } else {
      payload.concrete_inputs = concreteInputs;
    }
  }

  const response = await api.post('/api/analyze/code', payload);
  return {
    ...response.data,
    result: response.data?.result
      ? {
          ...response.data.result,
          source_code: response.data.result.source_code || code,
          concrete_inputs: response.data.result.concrete_inputs || payload.concrete_inputs,
        }
      : response.data?.result,
    source_code: code,
    concrete_inputs: payload.concrete_inputs,
  };
};

const attachSourceToPayload = (payload, code, concreteInputs) => ({
  ...payload,
  result: payload?.result
    ? {
        ...payload.result,
        source_code: payload.result.source_code || code,
        concrete_inputs: payload.result.concrete_inputs || concreteInputs,
      }
    : payload?.result,
  source_code: code,
  concrete_inputs: concreteInputs,
});

export const getModifiedCode = async (code, filename = 'code.py', concreteInputs = '', options = {}) => {
  const payload = { code, filename, async: true };

  if (concreteInputs) {
    if (typeof concreteInputs === 'string') {
      if (concreteInputs.trim()) payload.concrete_inputs = concreteInputs.trim();
    } else {
      payload.concrete_inputs = concreteInputs;
    }
  }

  const response = await api.post('/api/optimize/code', payload, { timeout: 0 });
  if (response.data?.job_id) {
    const jobResult = await pollAnalysisJob(response.data.job_id, {
      intervalMs: 700,
      timeoutMs: 900000,
      missingGraceMs: 60000,
      onProgress: (progressPayload) => {
        options.onProgress?.(attachSourceToPayload(progressPayload, code, payload.concrete_inputs));
      },
    });
    return attachSourceToPayload(jobResult, code, payload.concrete_inputs);
  }
  return attachSourceToPayload(response.data, code, payload.concrete_inputs);
};

export const pollAnalysisJob = async (jobId, options = {}) => {
  const intervalMs = options.intervalMs || 2500;
  const timeoutMs = options.timeoutMs || 150000;
  const missingGraceMs = options.missingGraceMs || 0;
  const startedAt = Date.now();
  let firstMissingAt = null;
  let lastPollError = null;
  let firstPoll = true;

  while (Date.now() - startedAt < timeoutMs) {
    if (firstPoll) {
      firstPoll = false;
    } else {
      await sleep(intervalMs);
    }
    try {
      const response = await api.get(`/api/analyze/jobs/${jobId}`, { timeout: 30000 });
      const payload = response.data;
      lastPollError = null;
      firstMissingAt = null;
      if (payload.status === 'completed') {
        return payload;
      }
      if (payload.status === 'failed') {
        throw new Error(payload.error || 'Backend analysis failed.');
      }
      if (payload.result) {
        options.onProgress?.(payload);
      }
    } catch (err) {
      if (err.response?.data?.status === 'failed') {
        throw new Error(err.response.data.error || 'Backend analysis failed.', { cause: err });
      }
      if (err.response?.status === 404) {
        if (missingGraceMs > 0) {
          firstMissingAt = firstMissingAt || Date.now();
          lastPollError = err;
          if (Date.now() - firstMissingAt < missingGraceMs) {
            continue;
          }
        }
        if (typeof options.onMissing === 'function') {
          return options.onMissing(err);
        }
        throw new Error(err.response.data?.error || 'Analysis job was not found.', { cause: err });
      }
      lastPollError = err;
    }
  }

  const detail = lastPollError ? ` Last poll error: ${getApiErrorMessage(lastPollError)}` : '';
  throw new Error(`Analysis is still running after ${Math.round(timeoutMs / 1000)} seconds.${detail}`);
};

export const inferInputs = async (code, filename = 'code.py') => {
  const response = await api.post('/api/analyze/inputs', { code, filename });
  return response.data;
};

export const analyzeZip = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/analyze/zip', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const fetchGithubFolders = async (url, path = '', ref = '') => {
  const payload = { url };
  if (path) payload.path = path;
  if (ref) payload.ref = ref;
  const response = await api.post('/api/analyze/github/folders', payload, { timeout: 0 });
  return response.data;
};

export const fetchGithubFiles = async (url, path = '', ref = '') => {
  const payload = { url };
  if (path) payload.path = path;
  if (ref) payload.ref = ref;
  try {
    const response = await api.post('/api/analyze/github/files', payload, { timeout: 0 });
    return response.data;
  } catch (err) {
    if (err.response && ![404, 405, 501, 502, 503, 504].includes(err.response.status)) {
      throw err;
    }
    const fallback = await api.post('/api/analyze/github/folders', payload, { timeout: 0 });
    return fallback.data;
  }
};

const GITHUB_CODE_EXTENSIONS = new Set([
  '.py', '.pyw',
  '.js', '.jsx', '.mjs', '.cjs',
  '.ts', '.tsx', '.mts', '.cts',
  '.java',
  '.cpp', '.cc', '.cxx', '.c++', '.hpp', '.hh', '.hxx', '.ipp',
  '.c', '.h',
]);

const GITHUB_SKIP_FOLDERS = new Set([
  'node_modules', '.git', '.hg', '.svn', '__pycache__', '.pytest_cache',
  '.mypy_cache', 'venv', '.venv', 'env', 'dist', 'build', '.next',
  'coverage', 'target', 'out', '.idea', '.vscode',
]);

const normalizeGithubPath = (path = '') => String(path || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');

const parseGithubRepository = (rawUrl = '') => {
  try {
    const parsed = new URL(/^https?:\/\//i.test(rawUrl) ? rawUrl : `https://${rawUrl}`);
    if (!['github.com', 'www.github.com'].includes(parsed.hostname.toLowerCase())) return null;
    const parts = parsed.pathname.split('/').filter(Boolean);
    if (parts.length < 2) return null;
    return {
      owner: parts[0],
      repo: parts[1].replace(/\.git$/i, ''),
    };
  } catch {
    return null;
  }
};

const isSkippedGithubPath = (path = '') => normalizeGithubPath(path)
  .split('/')
  .some(part => GITHUB_SKIP_FOLDERS.has(part.toLowerCase()));

const isSupportedGithubPath = (path = '') => {
  const cleanPath = normalizeGithubPath(path);
  const dot = cleanPath.lastIndexOf('.');
  const ext = dot >= 0 ? cleanPath.slice(dot).toLowerCase() : '';
  return GITHUB_CODE_EXTENSIONS.has(ext) && !isSkippedGithubPath(cleanPath);
};

const fileOptionForGithubPath = (path = '', selectedPath = '') => {
  const cleanPath = normalizeGithubPath(path);
  const cleanSelected = normalizeGithubPath(selectedPath);
  const prefix = cleanSelected ? `${cleanSelected}/` : '';
  return {
    path: cleanPath,
    label: prefix && cleanPath.startsWith(prefix) ? cleanPath.slice(prefix.length) : cleanPath,
    type: 'file',
  };
};

const fetchJson = async (url) => {
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Public repository file lookup failed: ${response.status}`);
  }
  return response.json();
};

export const fetchGithubFolderFilesPublic = async (url, path = '', ref = '') => {
  const repo = parseGithubRepository(url);
  if (!repo) return [];

  const selectedPath = normalizeGithubPath(path);
  const branch = ref || 'main';
  const encodedPath = selectedPath
    .split('/')
    .filter(Boolean)
    .map(part => encodeURIComponent(part))
    .join('/');
  const suffix = encodedPath ? `/contents/${encodedPath}` : '/contents';
  const endpoint = `https://api.github.com/repos/${encodeURIComponent(repo.owner)}/${encodeURIComponent(repo.repo)}${suffix}?ref=${encodeURIComponent(branch)}`;

  try {
    const payload = await fetchJson(endpoint);
    const items = Array.isArray(payload) ? payload : [payload];
    return items
      .filter(item => item?.type === 'file')
      .map(item => normalizeGithubPath(item.path))
      .filter(isSupportedGithubPath)
      .map(filePath => fileOptionForGithubPath(filePath, selectedPath));
  } catch {
    return [];
  }
};

export const fetchGithubFilesPublic = async (url, path = '', ref = '') => {
  const repo = parseGithubRepository(url);
  if (!repo) return [];

  const selectedPath = normalizeGithubPath(path);
  const branch = ref || 'main';
  const prefix = selectedPath ? `${selectedPath}/` : '';

  const fromJsDelivr = async () => {
    const endpoint = `https://data.jsdelivr.com/v1/package/gh/${encodeURIComponent(repo.owner)}/${encodeURIComponent(repo.repo)}@${encodeURIComponent(branch)}/flat`;
    const payload = await fetchJson(endpoint);
    return (payload.files || [])
      .map(item => normalizeGithubPath(String(item.name || '').replace(/^\/+/, '')))
      .filter(filePath => filePath && (!selectedPath || filePath.startsWith(prefix)))
      .filter(isSupportedGithubPath)
      .map(filePath => fileOptionForGithubPath(filePath, selectedPath));
  };

  const fromGithubTree = async () => {
    const endpoint = `https://api.github.com/repos/${encodeURIComponent(repo.owner)}/${encodeURIComponent(repo.repo)}/git/trees/${encodeURIComponent(branch)}?recursive=1`;
    const payload = await fetchJson(endpoint);
    return (payload.tree || [])
      .filter(item => item?.type === 'blob')
      .map(item => normalizeGithubPath(item.path))
      .filter(filePath => filePath && (!selectedPath || filePath.startsWith(prefix)))
      .filter(isSupportedGithubPath)
      .map(filePath => fileOptionForGithubPath(filePath, selectedPath));
  };

  try {
    return await fromJsDelivr();
  } catch {
    try {
      return await fromGithubTree();
    } catch {
      return [];
    }
  }
};

const postGithubAnalysis = async (payload) => {
  const response = await api.post('/api/analyze/github', payload, { timeout: 0 });
  return response.data;
};

export const analyzeGithub = async (url, path = '', ref = '') => {
  const selectedFile = isSupportedGithubPath(path);
  const payload = { url, async: !selectedFile };
  if (path) payload.path = path;
  if (ref) payload.ref = ref;

  const response = await api.post('/api/analyze/github', payload, { timeout: 0 });
  if (response.data?.job_id) {
    return pollAnalysisJob(response.data.job_id, {
      intervalMs: 2500,
      timeoutMs: 600000,
      onMissing: () => postGithubAnalysis({ ...payload, async: false }),
    });
  }
  return response.data;
};

export const downloadReport = async (analysisData, reportType = 'code') => {
  const response = await api.post(
    '/api/report',
    { analysis_data: analysisData, report_type: reportType },
    { responseType: 'blob' }
  );

  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'codescope_report.pdf');
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export default api;
