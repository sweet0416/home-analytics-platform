import { getApiData } from '@/api/client';

export interface DockerStatus {
  plugin: string;
  version: string;
  enabled: boolean;
  configured: boolean;
  reachable: boolean;
  docker_version: string | null;
  containers: number;
  running: number;
  problematic: number;
  error: string | null;
}

export interface DockerResourceResponse {
  data: Record<string, unknown>[];
}

export function fetchDockerStatus(): Promise<DockerStatus> {
  return getApiData<DockerStatus>('/docker/status');
}

export function fetchDockerContainers(): Promise<DockerResourceResponse> {
  return getApiData<DockerResourceResponse>('/docker/containers');
}

export function fetchDockerContainerStats(containerIds: string[] = []): Promise<DockerResourceResponse> {
  const query = containerIds.length
    ? `?ids=${containerIds.map((id) => encodeURIComponent(id)).join(',')}`
    : '';
  return getApiData<DockerResourceResponse>(`/docker/containers/stats${query}`);
}

export function fetchDockerImages(): Promise<DockerResourceResponse> {
  return getApiData<DockerResourceResponse>('/docker/images');
}

export function fetchDockerVolumes(): Promise<DockerResourceResponse> {
  return getApiData<DockerResourceResponse>('/docker/volumes');
}
