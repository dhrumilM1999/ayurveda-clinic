// The one place that talks to the backend API. ASK FIRST before editing.
// - Adds the login token and the current branch (X-Branch-ID) to every request.
// - When the short-lived token expires, gets a new one once, then retries.
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { tokenStore } from '../auth/tokenStore';
import { addStep, getSessionId, plainPath, sendReport } from '../errorLog/tracker';

export const api = axios.create({ baseURL: '/api/v1' });

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  const branch = tokenStore.getBranch();
  if (branch) config.headers['X-Branch-ID'] = branch;
  config.headers['X-Session-ID'] = getSessionId();
  return config;
});

let onSessionExpired: () => void = () => {};
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

let refreshing: Promise<string | null> | null = null;

/** Puts a failed call in the trail; tells the Error log when the server could not be reached or crashed. */
function noteFailedCall(failure: AxiosError) {
  const error = failure as AxiosError<{ code?: string }>;
  if (axios.isCancel(error)) return; // a search that was replaced by a newer one
  const method = (error.config?.method ?? 'get').toUpperCase();
  const path = plainPath(error.config?.url);
  const status = error.response?.status;
  addStep('api', `${method} ${path} ${status ?? 'no answer'}`);
  if (!error.response) {
    sendReport({ kind: 'network', message: `Could not reach the server: ${method} ${path}`, path, method });
  } else if (status && status >= 500 && error.response.data?.code) {
    // The server already wrote this one; add what the person did before it
    sendReport({ kind: 'trail', code: error.response.data.code, path, method, status_code: status });
  }
}

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
  (response) => {
    addStep('api', `${(response.config.method ?? 'get').toUpperCase()} ${plainPath(response.config.url)} ${response.status}`);
    return response;
  },
  async (error: AxiosError) => {
    noteFailedCall(error);
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
