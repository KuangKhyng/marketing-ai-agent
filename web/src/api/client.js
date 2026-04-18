import axios from 'axios';

const baseURL = import.meta.env.DEV
  ? 'http://localhost:8000/api'
  : '/api';

const api = axios.create({
  baseURL,
  timeout: 300000, // 5 min — LLM calls can be very slow on free tier
});

export const campaignAPI = {
  start: (input) => api.post('/campaigns/start', input),
  approveBrief: (runId, edit) => api.post(`/campaigns/${runId}/approve-brief`, edit),
  reviewStrategy: (runId, feedback) => api.post(`/campaigns/${runId}/review-strategy`, feedback),
  reviewContent: (runId, feedback) => api.post(`/campaigns/${runId}/review-content`, feedback),
  approveFinal: (runId) => api.post(`/campaigns/${runId}/approve-final`),
  quickAction: (runId, action) => api.post(`/campaigns/${runId}/quick-action`, action),
  download: (runId, format) => api.get(`/campaigns/${runId}/download/${format}`, { responseType: 'blob' }),
  history: () => api.get('/campaigns/history'),
};

export const brandsAPI = {
  list: () => api.get('/brands/'),
  get: (brandId) => api.get(`/brands/${brandId}`),
  create: (data) => api.post('/brands/', data),
  update: (brandId, data) => api.put(`/brands/${brandId}`, data),
  delete: (brandId) => api.delete(`/brands/${brandId}`),

  // Documents
  getDoc: (brandId, docPath) => api.get(`/brands/${brandId}/docs/${docPath}`),
  saveDoc: (brandId, docPath, content) => api.put(`/brands/${brandId}/docs/${docPath}`, { content }),
  deleteDoc: (brandId, docPath) => api.delete(`/brands/${brandId}/docs/${docPath}`),

  // Voice Profile
  getVoice: (brandId) => api.get(`/brands/${brandId}/voice-profile`),
  updateVoice: (brandId, profile) => api.put(`/brands/${brandId}/voice-profile`, { profile }),

  // Preview
  preview: (brandId) => api.get(`/brands/${brandId}/preview`),
};

export default api;
