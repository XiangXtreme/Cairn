export type DispatchSettingsMode = 'file' | 'ui';
export type WorkerType = 'claudecode' | 'codex' | 'pi' | 'mock';
export type ProviderKind = 'claudecode' | 'codex' | 'pi';
export type TaskType = 'bootstrap' | 'reason' | 'explore' | 'observe';
export type McpTransportType = 'stdio' | 'http';

export interface LeaseSettings {
  intent_timeout: number;
  reason_timeout: number;
}

export interface DispatchRuntimeSettings {
  interval: number;
  max_workers: number;
  max_running_projects: number;
  max_project_workers: number;
  healthcheck_timeout: number;
  prompt_group: string;
}

export interface DispatchTaskSettings {
  bootstrap: {
    timeout: number;
    conclude_timeout: number;
  };
  reason: {
    timeout: number;
    max_intents: number;
    allow_unavailable_dispatch: boolean;
    unavailable_fact_limit: number;
  };
  explore: {
    timeout: number;
    conclude_timeout: number;
  };
  observe: {
    enabled: boolean;
    timeout: number;
    min_interval_seconds: number;
    recent_run_limit: number;
    max_updates: number;
  };
}

export interface ProviderSettings {
  id: string;
  name: string;
  enabled: boolean;
  kind: ProviderKind;
  model: string;
  base_url: string;
  auth_token: string;
  has_auth_token: boolean;
  provider_api: string;
  context_window: number | null;
  extra_env: Record<string, string>;
}

export interface WorkerHealthcheckResponse {
  ok: boolean;
  worker_name: string;
  worker_type: WorkerType;
  returncode: number;
  duration_ms: number;
  http_status?: string | null;
  response_preview: string;
  stderr_preview: string;
  command: string;
}

export interface DispatchWorkerSettings {
  source_name: string;
  name: string;
  enabled: boolean;
  type: WorkerType;
  task_types: TaskType[];
  max_running: number;
  priority: number;
  provider_id: string;
  provider_supported: boolean;
  model: string;
  base_url: string;
  auth_token: string;
  has_auth_token: boolean;
  provider_api: string;
  context_window: number | null;
  extra_env: Record<string, string>;
  mcp_server_ids: string[];
  skill_ids: string[];
  mcp_supported: boolean;
  skill_supported: boolean;
}

export interface EditableWorkerSettings extends DispatchWorkerSettings {
  show_legacy_provider: boolean;
  healthcheck: WorkerHealthcheckResponse | null;
  is_testing_healthcheck: boolean;
}

export interface McpServerSettings {
  id: string;
  name: string;
  enabled: boolean;
  transport: McpTransportType;
  command: string;
  url: string;
  args: string[];
  env: Record<string, string>;
}

export interface SkillSettings {
  id: string;
  name: string;
  enabled: boolean;
  path: string;
  description: string;
  enabled_claude: boolean;
  enabled_codex: boolean;
}

export interface WorkerBindingSettings {
  worker_name: string;
  mcp_server_ids: string[];
  skill_ids: string[];
}

export interface DispatchModeInfo {
  mode: DispatchSettingsMode;
  source_path: string;
  compiled_path: string;
  hot_reload_enabled: boolean;
  compiled_updated_at?: string | null;
  last_validation_error: string;
}

export interface DispatchSettings {
  mode: DispatchSettingsMode;
  path: string;
  writable: boolean;
  runtime: DispatchRuntimeSettings;
  tasks: DispatchTaskSettings;
  workers: DispatchWorkerSettings[];
  mode_info: DispatchModeInfo;
  providers: ProviderSettings[];
  mcp_servers: McpServerSettings[];
  skills: SkillSettings[];
  worker_bindings: WorkerBindingSettings[];
  restart_required: boolean;
}

export interface EditableDispatchForm {
  runtime: DispatchRuntimeSettings;
  tasks: DispatchTaskSettings;
  workers: EditableWorkerSettings[];
  providers: ProviderSettings[];
  mcp_servers: McpServerSettings[];
  skills: SkillSettings[];
  worker_bindings: WorkerBindingSettings[];
}

export interface UpdateDispatchSettingsRequest {
  mode: DispatchSettingsMode;
  runtime: DispatchRuntimeSettings;
  tasks: DispatchTaskSettings;
  workers: DispatchWorkerSettings[];
  providers: ProviderSettings[];
  mcp_servers: McpServerSettings[];
  skills: SkillSettings[];
  worker_bindings: WorkerBindingSettings[];
}

export interface WorkerHealthcheckRequest {
  mode: DispatchSettingsMode;
  runtime: DispatchRuntimeSettings;
  worker: DispatchWorkerSettings;
  providers: ProviderSettings[];
  mcp_servers: McpServerSettings[];
  skills: SkillSettings[];
  worker_bindings: WorkerBindingSettings[];
}

export interface DiscoveredSkill {
  id: string;
  name: string;
  path: string;
  description: string;
  source: string;
  already_registered: boolean;
}

export interface SkillZipImportRequest {
  mode: DispatchSettingsMode;
  filename: string;
  content_base64: string;
}

export interface SkillZipImportResponse {
  imported_dir: string;
  discovered: DiscoveredSkill[];
}

export type ToastType = 'info' | 'success' | 'error';
