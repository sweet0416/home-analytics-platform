import { getApiData } from '@/api/client';
import type { DockerStatus } from '@/plugins/docker/api';
import type { PveStatus } from '@/plugins/pve/api';

export interface InfrastructureHealth {
  checked_at: string;
  healthy: boolean;
  configured_components: number;
  reachable_components: number;
  alerts: string[];
  docker: DockerStatus;
  pve: PveStatus;
}

export function fetchInfrastructureHealth(): Promise<InfrastructureHealth> {
  return getApiData<InfrastructureHealth>('/system/infrastructure-health');
}
