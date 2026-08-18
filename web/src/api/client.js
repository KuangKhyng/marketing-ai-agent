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

/**
 * Đọc luồng tiến trình SSE của một lần chạy.
 *
 * Dùng fetch thay vì EventSource vì EventSource không gửi được header,
 * mà endpoint này nằm sau X-API-Key.
 *
 * Promise resolve NGAY khi kết nối mở (server tạo hàng đợi ở thời điểm đó),
 * rồi đọc tiếp ở nền — nên phải await hàm này TRƯỚC khi POST, nếu không
 * event phát ra sớm sẽ rơi vào hư không.
 */
export async function streamProgress(runId, onEvent, signal) {
  const res = await fetch(`${baseURL}/campaigns/${runId}/events`, {
    headers: { 'X-API-Key': getAccessKey() },
    signal,
  });
  if (!res.ok || !res.body) return;

  (async () => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';

        for (const frame of frames) {
          const line = frame.split('\n').find(l => l.startsWith('data:'));
          if (!line) continue; // dòng ": keepalive"
          try {
            const event = JSON.parse(line.slice(5).trim());
            onEvent(event);
            if (event.type === 'done') return;
          } catch { /* frame lỗi thì bỏ qua, không làm hỏng cả luồng */ }
        }
      }
    } catch { /* abort hoặc mất mạng — tiến trình chỉ là phụ trợ */ }
  })();
}

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
  // Đọc lại một run đang dở — dùng khi mở link có ?run=<id> hoặc sau khi F5
  get: (runId) => api.get(`/campaigns/${runId}`),
  approveBrief: (runId, edit) => api.post(`/campaigns/${runId}/approve-brief`, edit),
  reviewStrategy: (runId, feedback) => api.post(`/campaigns/${runId}/review-strategy`, feedback),
  reviewContent: (runId, feedback) => api.post(`/campaigns/${runId}/review-content`, feedback),
  // Nhánh "retry" của LangGraph, do người dùng bấm
  retryContent: (runId) => api.post(`/campaigns/${runId}/retry-content`),
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

  // Nạp liệu — hai chặng chỉ trả về đề xuất, apply mới ghi.
  // Extract chạy LLM nên chậm hơn timeout mặc định của trang khác.
  bootstrapVoice: (brandId, samples) =>
    api.post(`/brands/${brandId}/bootstrap/voice`, { samples }),
  bootstrapBrand: (brandId, documents) =>
    api.post(`/brands/${brandId}/bootstrap/brand`, { documents }),
  bootstrapApply: (brandId, payload) =>
    api.post(`/brands/${brandId}/bootstrap/apply`, payload),

  // Tạo brand TỪ tài liệu: đọc trước (chưa tạo gì), duyệt rồi mới tạo
  bootstrapPreview: (payload) => api.post('/brands/bootstrap/preview', payload),
  bootstrapCreate: (payload) => api.post('/brands/bootstrap/create', payload),
};

export const templatesAPI = {
  list: () => api.get('/templates/'),
  get: (id) => api.get(`/templates/${id}`),
  create: (data) => api.post('/templates/', data),
  delete: (id) => api.delete(`/templates/${id}`),
};

export default api;
