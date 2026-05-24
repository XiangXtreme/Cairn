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
import type {
  CloneProjectRequest,
  CompleteRequest,
  ConcludeRequest,
  ConcludeResponse,
  CreateHintRequest,
  CreateIntentRequest,
  CreateProjectRequest,
  HeartbeatRequest,
  Hint,
  Intent,
  ProjectDetail,
  ProjectMeta,
  ProjectSummary,
  ReopenRequest,
  ReopenResponse,
  UpdateProjectStatusRequest,
  UpdateProjectTitleRequest,
} from '@/types/workspace';

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
  listProjects() {
    return request<ProjectSummary[]>('GET', '/projects');
  },
  getProject(projectId: string) {
    return request<ProjectDetail>('GET', `/projects/${projectId}`);
  },
  createProject(body: CreateProjectRequest) {
    return request<ProjectDetail>('POST', '/projects', body);
  },
  cloneProject(projectId: string, body: CloneProjectRequest) {
    return request<ProjectDetail>('POST', `/projects/${projectId}/clone`, body);
  },
  deleteProject(projectId: string) {
    return request<void>('DELETE', `/projects/${projectId}`);
  },
  updateProjectTitle(projectId: string, body: UpdateProjectTitleRequest) {
    return request<ProjectMeta>('PUT', `/projects/${projectId}/title`, body);
  },
  updateProjectStatus(projectId: string, body: UpdateProjectStatusRequest) {
    return request<ProjectMeta>('PUT', `/projects/${projectId}/status`, body);
  },
  completeProject(projectId: string, body: CompleteRequest) {
    return request<Intent>('POST', `/projects/${projectId}/complete`, body);
  },
  reopenProject(projectId: string, body: ReopenRequest) {
    return request<ReopenResponse>('POST', `/projects/${projectId}/reopen`, body);
  },
  createHint(projectId: string, body: CreateHintRequest) {
    return request<Hint>('POST', `/projects/${projectId}/hints`, body);
  },
  createIntent(projectId: string, body: CreateIntentRequest) {
    return request<Intent>('POST', `/projects/${projectId}/intents`, body);
  },
  heartbeatIntent(projectId: string, intentId: string, body: HeartbeatRequest) {
    return request<Intent>('POST', `/projects/${projectId}/intents/${intentId}/heartbeat`, body);
  },
  releaseIntent(projectId: string, intentId: string, body: HeartbeatRequest) {
    return request<Intent>('POST', `/projects/${projectId}/intents/${intentId}/release`, body);
  },
  concludeIntent(projectId: string, intentId: string, body: ConcludeRequest) {
    return request<ConcludeResponse>('POST', `/projects/${projectId}/intents/${intentId}/conclude`, body);
  },
  exportProject(projectId: string, format: 'yaml' | 'timeline' = 'yaml') {
    return requestText(`/projects/${projectId}/export?format=${format}`);
  },
};

async function requestText(path: string): Promise<string> {
  const response = await fetch(path);
  const text = await response.text();
  if (!response.ok) {
    try {
      const payload = JSON.parse(text) as { detail?: string };
      throw new Error(payload.detail || `HTTP ${response.status}`);
    } catch {
      throw new Error(text || `HTTP ${response.status}`);
    }
  }
  return text;
}
