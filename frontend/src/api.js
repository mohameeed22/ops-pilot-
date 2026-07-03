import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
});

api.interceptors.request.use(config => {
  const token = localStorage.getItem('opspilot_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const login       = (data)                => api.post('/auth/login', data, { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }).then(r => r.data);
export const getMe       = ()                    => api.get('/auth/me').then(r => r.data);
export const fetchStats  = ()                    => api.get('/stats').then(r => r.data);
export const fetchRuns   = (params = {})         => api.get('/runs', { params }).then(r => r.data);
export const fetchRun    = (runId)               => api.get(`/runs/${runId}`).then(r => r.data);
export const fetchAudit  = (params = {})         => api.get('/audit', { params }).then(r => r.data);
export const fetchHealth = ()                    => axios.get(`${BASE_URL}/health`).then(r => r.data);
export const fetchReady  = ()                    => axios.get(`${BASE_URL}/ready`).then(r => r.data);

export default api;
