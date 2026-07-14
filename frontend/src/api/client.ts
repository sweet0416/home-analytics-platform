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

export async function getApiData<T>(url: string): Promise<T> {
  const response = await apiClient.get<ApiResponse<T>>(url);
  return response.data.data;
}

