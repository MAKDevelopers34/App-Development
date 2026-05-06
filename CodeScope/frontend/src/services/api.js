import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

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
  const response = await api.post('/api/analyze/code', payload);
  return response.data;
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
