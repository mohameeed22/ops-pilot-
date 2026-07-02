import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY  = import.meta.env.VITE_API_KEY  || '';

const api = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'X-API-Key': API_KEY },
});

export const fetchStats  = ()                    => api.get('/stats').then(r => r.data);
export const fetchRuns   = (params = {})         => api.get('/runs', { params }).then(r => r.data);
export const fetchRun    = (runId)               => api.get(`/runs/${runId}`).then(r => r.data);
export const fetchAudit  = (params = {})         => api.get('/audit', { params }).then(r => r.data);
export const fetchHealth = ()                    => axios.get(`${BASE_URL}/health`).then(r => r.data);
export const fetchReady  = ()                    => axios.get(`${BASE_URL}/ready`).then(r => r.data);

export default api;
