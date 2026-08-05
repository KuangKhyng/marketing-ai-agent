import axios from 'axios';

const baseURL = import.meta.env.DEV
  ? 'http://localhost:8000/api'
  : '/api';

const STORAGE_KEY = 'mkt_access_key';

export const getAccessKey = () => localStorage.getItem(STORAGE_KEY) || '';
export const setAccessKey = (key) => localStorage.setItem(STORAGE_KEY, key);
export const clearAccessKey = () => localStorage.removeItem(STORAGE_KEY);

const api = axios.create({
  baseURL,
  timeout: 300000, // 5 min — LLM calls can be very slow on free tier
});

// Gắn access key vào mọi request
api.interceptors.request.use((config) => {
  const key = getAccessKey();
  if (key) config.headers['X-API-Key'] = key;
  return config;
});

// Key sai/hết hạn → xóa key và quay về màn hình đăng nhập.
// Bỏ qua với request có cờ _skipAuthHandler (dùng khi đang verify key mới).
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && !error.config?._skipAuthHandler) {
      clearAccessKey();
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  // Public — không cần key
  status: () => api.get('/auth/status', { _skipAuthHandler: true }),
  // Kiểm tra một key cụ thể mà không lưu trước
  verify: (key) => api.get('/auth/verify', {
    headers: { 'X-API-Key': key },
    _skipAuthHandler: true,
  }),
};

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

export const templatesAPI = {
  list: () => api.get('/templates/'),
  get: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates/', data),
  delete: (id) => api.delete(`/templates/${id}`),
};

export default api;
