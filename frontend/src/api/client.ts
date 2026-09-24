import axios from 'axios';

export interface ApiResponse<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
  trace_id: string | null;
}

export const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
});

let csrfToken = '';

export function setCsrfToken(value: string): void {
  csrfToken = value;
}

apiClient.interceptors.request.use((config) => {
  if (csrfToken && !['get', 'head'].includes(config.method?.toLowerCase() ?? '')) {
    config.headers.set('X-CSRF-Token', csrfToken);
  }
  return config;
});

apiClient.interceptors.response.use(undefined, (error) => {
  if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/')) {
    setCsrfToken('');
    if (window.location.pathname !== '/login') {
      window.location.assign(`/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`);
    }
  }
  return Promise.reject(error);
});

export async function getApiData<T>(url: string, options?: { timeout?: number }): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url, options);
  return response.data.data;
}

export async function postApiData<T, P extends object>(
  url: string,
  payload: P,
  options?: { timeout?: number; headers?: Record<string, string> },
): Promise<T> {
  const response = await apiClient.post<ApiResponse<T>>(url, payload, options);
  return response.data.data;
}

export async function patchApiData<T, P extends object>(url: string, payload: P): Promise<T> {
  const response = await apiClient.patch<ApiResponse<T>>(url, payload);
  return response.data.data;
}

export async function deleteApiData<T>(url: string): Promise<T> {
  const response = await apiClient.delete<ApiResponse<T>>(url);
  return response.data.data;
}

export async function downloadApiFile(url: string, filename: string): Promise<void> {
  let blob: Blob;
  try {
    const response = await apiClient.get<Blob>(url.replace(/^\/api\/v1/, ''), { responseType: 'blob' });
    blob = response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 401) return;
    throw error;
  }

  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}
