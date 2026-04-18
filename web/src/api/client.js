import axios from 'axios';

const baseURL = import.meta.env.DEV
  ? 'http://localhost:8000/api'
  : '/api';

const api = axios.create({
  baseURL,
  timeout: 120000, // 2 min — LLM calls can be slow
});

export const campaignAPI = {
  start: (input) => api.post('/campaigns/start', input),
  approveBrief: (runId, edit) => api.post(`/campaigns/${runId}/approve-brief`, edit),
  reviewStrategy: (runId, feedback) => api.post(`/campaigns/${runId}/review-strategy`, feedback),
  reviewContent: (runId, feedback) => api.post(`/campaigns/${runId}/review-content`, feedback),
  approveFinal: (runId) => api.post(`/campaigns/${runId}/approve-final`),
  download: (runId, format) => api.get(`/campaigns/${runId}/download/${format}`, { responseType: 'blob' }),
  history: () => api.get('/campaigns/history'),
};

export default api;
