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
        throw new Error(err.response.data.error || 'Backend analysis failed.', { cause: err });
      }
      if (err.response?.status === 404) {
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

export const analyzeGithub = async (url) => {
  const response = await api.post('/api/analyze/github', { url });
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
