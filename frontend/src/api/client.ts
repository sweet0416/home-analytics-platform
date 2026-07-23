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

export async function getApiData<T>(url: string, options?: { timeout?: number }): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url, options);
  return response.data.data;
}

export async function postApiData<T, P extends object>(
  url: string,
  payload: P,
  options?: { timeout?: number },
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
