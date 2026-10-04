// The one place that talks to the backend API. ASK FIRST before editing.
// - Adds the login token and the current branch (X-Branch-ID) to every request.
// - When the short-lived token expires, gets a new one once, then retries.
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { tokenStore } from '../auth/tokenStore';

export const api = axios.create({ baseURL: '/api/v1' });

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const branch = tokenStore.getBranch();
  if (branch) config.headers['X-Branch-ID'] = branch;
  return config;
});

let onSessionExpired: () => void = () => {};
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post('/api/v1/auth/refresh/', { refresh });
    tokenStore.setTokens(data.access, data.refresh);
    return data.access as string;
  } catch {
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retried && tokenStore.getRefresh()) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const newToken = await refreshing;
      refreshing = null;
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      }
      tokenStore.clear();
      onSessionExpired();
    }
    return Promise.reject(error);
  },
);

/** Turn an API error into a short message to show on screen. */
export function errorMessage(error: unknown, fallback: string): string {
  const data = (error as AxiosError<Record<string, unknown>>)?.response?.data;
  if (!data || typeof data !== 'object') return fallback;
  if (typeof data.detail === 'string') return data.detail;
  const parts: string[] = [];
  for (const [field, value] of Object.entries(data)) {
    const text = Array.isArray(value) ? value.map(String).join(' ') : typeof value === 'string' ? value : '';
    if (text) parts.push(field === 'non_field_errors' ? text : `${field}: ${text}`);
  }
  return parts.join(' • ') || fallback;
}
