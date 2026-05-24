import axios from 'axios';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000'
).replace(/\/+$/, '');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

const sleep = (ms) => new Promise(resolve => window.setTimeout(resolve, ms));

export const getApiErrorMessage = (err) => {
  if (err.message && !err.response) return err.message;

  const backendError = err.response?.data?.error;
  if (backendError) return backendError;

  if (err.response?.status) {
    return `Backend request failed with HTTP ${err.response.status} at ${API_BASE_URL}. Check the API Gateway route/method forwarding.`;
  }

  return `Could not reach the backend at ${API_BASE_URL}. Check VITE_API_BASE_URL and make sure the API is deployed.`;
};

// ─── Analyze pasted code ────────────────────────────────────
export const analyzeCode = async (code, filename = 'code.py', concreteInputs = '') => {
  const payload = { code, filename };
  if (concreteInputs) {
    if (typeof concreteInputs === 'string') {
      if (concreteInputs.trim()) payload.concrete_inputs = concreteInputs.trim();
    } else {
      payload.concrete_inputs = concreteInputs;
    }
  }
  const response = await api.post('/api/analyze/code', { ...payload, async: true });
  if (response.data?.job_id) {
    return pollAnalysisJob(response.data.job_id);
  }
  return response.data;
};

export const pollAnalysisJob = async (jobId, options = {}) => {
  const intervalMs = options.intervalMs || 2500;
  const timeoutMs = options.timeoutMs || 150000;
  const startedAt = Date.now();
  let lastPollError = null;

  while (Date.now() - startedAt < timeoutMs) {
    await sleep(intervalMs);
    try {
      const response = await api.get(`/api/analyze/jobs/${jobId}`, { timeout: 30000 });
      const payload = response.data;
      lastPollError = null;
      if (payload.status === 'completed' || payload.result) {
        return payload;
      }
      if (payload.status === 'failed') {
        throw new Error(payload.error || 'Backend analysis failed.');
      }
    } catch (err) {
      if (err.response?.data?.status === 'failed') {
        throw new Error(err.response.data.error || 'Backend analysis failed.');
      }
      if (err.response?.status === 404) {
        throw new Error(err.response.data?.error || 'Analysis job was not found.');
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

// ─── Analyze ZIP file ───────────────────────────────────────
export const analyzeZip = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/api/analyze/zip', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// ─── Analyze GitHub URL ─────────────────────────────────────
export const analyzeGithub = async (url) => {
  const response = await api.post('/api/analyze/github', { url });
  return response.data;
};

// ─── Download PDF report ────────────────────────────────────
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
};

export default api;
