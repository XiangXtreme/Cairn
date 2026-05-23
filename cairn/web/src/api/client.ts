import type {
  DispatchSettings,
  DispatchSettingsMode,
  DiscoveredSkill,
  LeaseSettings,
  SkillZipImportRequest,
  SkillZipImportResponse,
  UpdateDispatchSettingsRequest,
  WorkerHealthcheckRequest,
  WorkerHealthcheckResponse,
} from '@/types/dispatch';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const init: RequestInit = { method, headers };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }

  const response = await fetch(path, init);
  if (response.status === 204) return null as T;

  const text = await response.text();
  let payload: unknown = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      const detail = (payload as { detail: unknown }).detail;
      if (typeof detail === 'string') message = detail;
      else if (Array.isArray(detail)) {
        message = detail
          .map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : String(item)))
          .join('; ');
      }
    } else if (typeof payload === 'string' && payload.trim()) {
      message = payload;
    }
    throw new Error(message);
  }

  return payload as T;
}

function modeQuery(mode?: DispatchSettingsMode): string {
  return mode ? `?mode=${encodeURIComponent(mode)}` : '';
}

export const api = {
  getLeaseSettings() {
    return request<LeaseSettings>('GET', '/settings');
  },
  saveLeaseSettings(body: LeaseSettings) {
    return request<LeaseSettings>('PUT', '/settings', body);
  },
  getDispatchSettings(mode?: DispatchSettingsMode) {
    return request<DispatchSettings>('GET', `/settings/dispatch${modeQuery(mode)}`);
  },
  saveDispatchSettings(body: UpdateDispatchSettingsRequest) {
    return request<DispatchSettings>('PUT', '/settings/dispatch', body);
  },
  testWorkerHealthcheck(body: WorkerHealthcheckRequest) {
    return request<WorkerHealthcheckResponse>('POST', '/settings/dispatch/workers/healthcheck', body);
  },
  discoverSkills(mode?: DispatchSettingsMode) {
    return request<DiscoveredSkill[]>('GET', `/settings/dispatch/skills/discover${modeQuery(mode)}`);
  },
  importSkillZip(body: SkillZipImportRequest) {
    return request<SkillZipImportResponse>('POST', '/settings/dispatch/skills/import-zip', body);
  },
};
