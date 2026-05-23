import { defineStore } from 'pinia';
import { computed, reactive, ref } from 'vue';

import { api } from '@/api/client';
import type {
  DispatchModeInfo,
  DispatchSettings,
  DispatchSettingsMode,
  DispatchTaskSettings,
  EditableDispatchForm,
  EditableWorkerSettings,
  LeaseSettings,
  McpServerSettings,
  ProviderSettings,
  SkillSettings,
  TaskType,
  UpdateDispatchSettingsRequest,
  WorkerHealthcheckResponse,
  WorkerType,
} from '@/types/dispatch';
import { useUiStore } from '@/stores/ui';

const TASK_ORDER: TaskType[] = ['bootstrap', 'reason', 'explore', 'observe'];
const INTERNAL_ENV_KEYS = new Set(['CAIRN_PROVIDER_SPEC', 'CAIRN_MCP_SERVERS', 'CAIRN_SKILLS']);

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function defaultTasks(): DispatchTaskSettings {
  return {
    bootstrap: { timeout: 300, conclude_timeout: 90 },
    reason: {
      timeout: 300,
      max_intents: 1,
      allow_unavailable_dispatch: false,
      unavailable_fact_limit: 2,
    },
    explore: { timeout: 300, conclude_timeout: 90 },
    observe: {
      enabled: false,
      timeout: 300,
      min_interval_seconds: 60,
      recent_run_limit: 10,
      max_updates: 4,
    },
  };
}

function normalizeTasks(tasks?: Partial<DispatchTaskSettings>): DispatchTaskSettings {
  const fallback = defaultTasks();
  return {
    bootstrap: {
      timeout: Number(tasks?.bootstrap?.timeout || fallback.bootstrap.timeout),
      conclude_timeout: Number(tasks?.bootstrap?.conclude_timeout || fallback.bootstrap.conclude_timeout),
    },
    reason: {
      timeout: Number(tasks?.reason?.timeout || fallback.reason.timeout),
      max_intents: Number(tasks?.reason?.max_intents || fallback.reason.max_intents),
      allow_unavailable_dispatch: tasks?.reason?.allow_unavailable_dispatch === true,
      unavailable_fact_limit: Number(
        tasks?.reason?.unavailable_fact_limit || fallback.reason.unavailable_fact_limit,
      ),
    },
    explore: {
      timeout: Number(tasks?.explore?.timeout || fallback.explore.timeout),
      conclude_timeout: Number(tasks?.explore?.conclude_timeout || fallback.explore.conclude_timeout),
    },
    observe: {
      enabled: tasks?.observe?.enabled === true,
      timeout: Number(tasks?.observe?.timeout || fallback.observe.timeout),
      min_interval_seconds: Number(
        tasks?.observe?.min_interval_seconds || fallback.observe.min_interval_seconds,
      ),
      recent_run_limit: Number(tasks?.observe?.recent_run_limit || fallback.observe.recent_run_limit),
      max_updates: Number(tasks?.observe?.max_updates || fallback.observe.max_updates),
    },
  };
}

function sanitizeExtraEnv(env: Record<string, string> | undefined): Record<string, string> {
  return Object.fromEntries(
    Object.entries(env || {})
      .filter(([key]) => key.trim() && !INTERNAL_ENV_KEYS.has(key.trim()))
      .map(([key, value]) => [key.trim(), String(value ?? '')]),
  );
}

function normalizeWorker(worker: Partial<EditableWorkerSettings>): EditableWorkerSettings {
  const type = (worker.type || 'codex') as WorkerType;
  const extraEnv = sanitizeExtraEnv(worker.extra_env);
  const hasDirectConfig = Boolean(
    worker.model
      || worker.base_url
      || worker.has_auth_token
      || worker.provider_api
      || worker.context_window,
  );
  return {
    source_name: worker.source_name || worker.name || '',
    name: worker.name || '',
    enabled: worker.enabled !== false,
    type,
    task_types: Array.isArray(worker.task_types) && worker.task_types.length
      ? TASK_ORDER.filter((task) => worker.task_types?.includes(task))
      : ['bootstrap', 'reason', 'explore'],
    max_running: Number(worker.max_running || 1),
    priority: Number(worker.priority || 0),
    provider_id: worker.provider_id || '',
    provider_supported: worker.provider_supported !== false && type !== 'mock',
    model: worker.model || '',
    base_url: worker.base_url || '',
    auth_token: '',
    has_auth_token: worker.has_auth_token === true,
    provider_api: worker.provider_api || '',
    context_window: worker.context_window ?? null,
    extra_env: extraEnv,
    mcp_server_ids: Array.isArray(worker.mcp_server_ids) ? [...worker.mcp_server_ids] : [],
    skill_ids: Array.isArray(worker.skill_ids) ? [...worker.skill_ids] : [],
    mcp_supported: worker.mcp_supported !== false && ['claudecode', 'codex'].includes(type),
    skill_supported: worker.skill_supported === true || ['claudecode', 'codex'].includes(type),
    show_direct_config: !worker.provider_id && hasDirectConfig,
    show_runtime_env: Object.keys(extraEnv).length > 0,
    healthcheck: null,
    is_testing_healthcheck: false,
  };
}

function serializeWorker(worker: EditableWorkerSettings) {
  return {
    source_name: worker.source_name || '',
    name: worker.name || '',
    enabled: worker.enabled !== false,
    type: worker.type,
    task_types: TASK_ORDER.filter((task) => worker.task_types.includes(task)),
    max_running: Number(worker.max_running || 1),
    priority: Number(worker.priority || 0),
    provider_id: worker.provider_id || '',
    provider_supported: worker.provider_supported !== false,
    model: worker.model || '',
    base_url: worker.base_url || '',
    auth_token: worker.auth_token || '',
    has_auth_token: worker.has_auth_token === true,
    provider_api: worker.provider_api || '',
    context_window: worker.context_window === null || worker.context_window === undefined || worker.context_window === 0
      ? null
      : Number(worker.context_window),
    extra_env: sanitizeExtraEnv(worker.extra_env),
    mcp_server_ids: Array.isArray(worker.mcp_server_ids) ? [...worker.mcp_server_ids] : [],
    skill_ids: Array.isArray(worker.skill_ids) ? [...worker.skill_ids] : [],
    mcp_supported: worker.mcp_supported !== false,
    skill_supported: worker.skill_supported === true,
  };
}

function defaultModeInfo(): DispatchModeInfo {
  return {
    mode: 'file',
    source_path: '',
    compiled_path: '',
    hot_reload_enabled: true,
    compiled_updated_at: '',
    last_validation_error: '',
  };
}

function defaultForm(): EditableDispatchForm {
  return {
    runtime: {
      interval: 3,
      max_workers: 1,
      max_running_projects: 1,
      max_project_workers: 1,
      healthcheck_timeout: 20,
      prompt_group: 'default',
    },
    tasks: defaultTasks(),
    workers: [],
    providers: [],
    mcp_servers: [],
    skills: [],
    worker_bindings: [],
  };
}

function normalizeProvider(provider: Partial<ProviderSettings>): ProviderSettings {
  return {
    id: provider.id || '',
    name: provider.name || '',
    enabled: provider.enabled !== false,
    kind: provider.kind || 'codex',
    model: '',
    base_url: provider.base_url || '',
    auth_token: '',
    has_auth_token: provider.has_auth_token === true,
    provider_api: '',
    context_window: null,
    extra_env: sanitizeExtraEnv(provider.extra_env),
  };
}

function normalizeMcpServer(server: Partial<McpServerSettings>): McpServerSettings {
  return {
    id: server.id || '',
    name: server.name || '',
    enabled: server.enabled !== false,
    transport: server.transport || 'stdio',
    command: server.command || '',
    url: server.url || '',
    args: Array.isArray(server.args) ? [...server.args] : [],
    env: sanitizeExtraEnv(server.env),
  };
}

function normalizeSkill(skill: Partial<SkillSettings>): SkillSettings {
  return {
    id: skill.id || '',
    name: skill.name || '',
    enabled: skill.enabled !== false,
    path: skill.path || '',
    description: skill.description || '',
    enabled_claude: skill.enabled_claude === true,
    enabled_codex: skill.enabled_codex === true,
  };
}

export const useDispatchSettingsStore = defineStore('dispatchSettings', () => {
  const ui = useUiStore();
  const leaseSettings = reactive<LeaseSettings>({ intent_timeout: 5, reason_timeout: 5 });
  const form = reactive<EditableDispatchForm>(defaultForm());
  const mode = ref<DispatchSettingsMode>('file');
  const meta = reactive({
    path: '',
    writable: false,
    restart_required: false,
    source_path: '',
    compiled_path: '',
    hot_reload_enabled: true,
    compiled_updated_at: '',
    last_validation_error: '',
  });
  const loadError = ref('');
  const isLoading = ref(false);
  const isSaving = ref(false);
  const discoveredSkills = ref<import('@/types/dispatch').DiscoveredSkill[]>([]);

  const enabledWorkerCount = computed(() => form.workers.filter((worker) => worker.enabled !== false).length);
  const enabledProviderCount = computed(() => form.providers.filter((provider) => provider.enabled !== false).length);
  const enabledMcpCount = computed(() => form.mcp_servers.filter((server) => server.enabled !== false).length);
  const enabledSkillCount = computed(() => form.skills.filter((skill) => skill.enabled !== false).length);

  function applyDispatchSettings(settings: DispatchSettings) {
    mode.value = settings.mode || mode.value;
    Object.assign(meta, {
      path: settings.path || '',
      writable: settings.writable === true,
      restart_required: settings.restart_required === true,
      source_path: settings.mode_info?.source_path || '',
      compiled_path: settings.mode_info?.compiled_path || settings.path || '',
      hot_reload_enabled: settings.mode_info?.hot_reload_enabled !== false,
      compiled_updated_at: settings.mode_info?.compiled_updated_at || '',
      last_validation_error: settings.mode_info?.last_validation_error || '',
    });

    const normalized = {
      runtime: { ...settings.runtime },
      tasks: normalizeTasks(settings.tasks),
      providers: (settings.providers || []).map(normalizeProvider),
      workers: (settings.workers || []).map(normalizeWorker),
      mcp_servers: (settings.mcp_servers || []).map(normalizeMcpServer),
      skills: (settings.skills || []).map(normalizeSkill),
      worker_bindings: (settings.worker_bindings || []).map((binding) => ({
        worker_name: binding.worker_name || '',
        mcp_server_ids: Array.isArray(binding.mcp_server_ids) ? [...binding.mcp_server_ids] : [],
        skill_ids: Array.isArray(binding.skill_ids) ? [...binding.skill_ids] : [],
      })),
    };

    Object.assign(form, normalized);
  }

  async function loadLeaseSettings() {
    const settings = await api.getLeaseSettings();
    leaseSettings.intent_timeout = settings.intent_timeout;
    leaseSettings.reason_timeout = settings.reason_timeout;
  }

  async function saveLeaseSettings() {
    const saved = await api.saveLeaseSettings({ ...leaseSettings });
    leaseSettings.intent_timeout = saved.intent_timeout;
    leaseSettings.reason_timeout = saved.reason_timeout;
    ui.showToast('服务端超时已保存', 'success');
  }

  async function loadDispatchSettings(nextMode?: DispatchSettingsMode) {
    isLoading.value = true;
    loadError.value = '';
    try {
      const settings = await api.getDispatchSettings(nextMode || mode.value || undefined);
      applyDispatchSettings(settings);
    } catch (error) {
      loadError.value = error instanceof Error ? error.message : String(error);
      ui.showToast(loadError.value, 'error');
    } finally {
      isLoading.value = false;
    }
  }

  async function setMode(nextMode: DispatchSettingsMode) {
    if (nextMode === mode.value) return;
    mode.value = nextMode;
    await loadDispatchSettings(nextMode);
  }

  function serializePayload(): UpdateDispatchSettingsRequest {
    return {
      mode: mode.value,
      runtime: { ...form.runtime },
      tasks: normalizeTasks(form.tasks),
      providers: form.providers.map((provider) => ({
        id: provider.id || '',
        name: provider.name || '',
        enabled: provider.enabled !== false,
        kind: provider.kind || 'codex',
        model: '',
        base_url: provider.base_url || '',
        auth_token: provider.auth_token || '',
        has_auth_token: provider.has_auth_token === true,
        provider_api: '',
        context_window: null,
        extra_env: sanitizeExtraEnv(provider.extra_env),
      })),
      workers: form.workers.map(serializeWorker),
      mcp_servers: form.mcp_servers.map((server) => ({
        ...server,
        args: Array.isArray(server.args) ? server.args.filter((arg) => arg.trim()) : [],
        env: sanitizeExtraEnv(server.env),
      })),
      skills: form.skills.map((skill) => ({ ...skill })),
      worker_bindings: form.workers.map((worker) => ({
        worker_name: worker.name || '',
        mcp_server_ids: Array.isArray(worker.mcp_server_ids) ? [...worker.mcp_server_ids] : [],
        skill_ids: Array.isArray(worker.skill_ids) ? [...worker.skill_ids] : [],
      })),
    };
  }

  async function saveDispatchSettings() {
    const validationError = validateProviderBindings();
    if (validationError) {
      ui.showToast(validationError, 'error');
      return;
    }
    isSaving.value = true;
    try {
      const saved = await api.saveDispatchSettings(serializePayload());
      applyDispatchSettings(saved);
      ui.showToast('Worker 配置已保存', 'success');
    } catch (error) {
      ui.showToast(error instanceof Error ? error.message : String(error), 'error');
    } finally {
      isSaving.value = false;
    }
  }

  async function testWorkerHealthcheck(worker: EditableWorkerSettings) {
    if (worker.is_testing_healthcheck || worker.type === 'mock') return;
    worker.is_testing_healthcheck = true;
    worker.healthcheck = null;
    try {
      const result = await api.testWorkerHealthcheck({
        mode: mode.value,
        runtime: { ...form.runtime },
        worker: serializeWorker(worker),
        providers: serializePayload().providers,
        mcp_servers: serializePayload().mcp_servers,
        skills: serializePayload().skills,
        worker_bindings: serializePayload().worker_bindings,
      });
      worker.healthcheck = result;
      ui.showToast(result.ok ? `Worker ${worker.name} 测试成功` : `Worker ${worker.name} 测试失败`, result.ok ? 'success' : 'error');
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      worker.healthcheck = {
        ok: false,
        worker_name: worker.name || '',
        worker_type: worker.type,
        returncode: 1,
        duration_ms: 0,
        http_status: '',
        response_preview: '',
        stderr_preview: message,
        command: '',
      } satisfies WorkerHealthcheckResponse;
      ui.showToast(message, 'error');
    } finally {
      worker.is_testing_healthcheck = false;
    }
  }

  function blankWorker(): EditableWorkerSettings {
    return normalizeWorker({
      source_name: '',
      name: `worker_${form.workers.length + 1}`,
      enabled: true,
      type: 'codex',
      task_types: ['bootstrap', 'reason', 'explore'],
      max_running: 1,
      priority: 0,
      provider_supported: true,
      mcp_supported: true,
      skill_supported: true,
    });
  }

  function blankProvider(): ProviderSettings {
    return normalizeProvider({
      id: `provider_${form.providers.length + 1}`,
      name: '',
      enabled: true,
    });
  }

  function blankMcpServer(): McpServerSettings {
    return normalizeMcpServer({
      id: `mcp_${form.mcp_servers.length + 1}`,
      name: '',
      enabled: true,
      transport: 'stdio',
    });
  }

  function blankSkill(): SkillSettings {
    return normalizeSkill({
      id: `skill_${form.skills.length + 1}`,
      name: '',
      enabled: true,
    });
  }

  function addWorker() {
    form.workers.push(blankWorker());
  }

  function removeWorker(index: number) {
    form.workers.splice(index, 1);
  }

  function toggleWorkerEnabled(worker: EditableWorkerSettings) {
    worker.enabled = worker.enabled === false;
  }

  function onWorkerTypeChange(worker: EditableWorkerSettings) {
    if (worker.type !== 'pi') {
      worker.provider_api = '';
      worker.context_window = null;
    } else if (!worker.provider_api) {
      worker.provider_api = 'openai-completions';
    }
    if (worker.type === 'mock') {
      worker.provider_id = '';
      worker.model = '';
      worker.base_url = '';
      worker.auth_token = '';
      worker.show_direct_config = false;
      worker.show_runtime_env = false;
    }
    worker.provider_supported = worker.type !== 'mock';
    worker.mcp_supported = ['claudecode', 'codex'].includes(worker.type);
    worker.skill_supported = ['claudecode', 'codex'].includes(worker.type);
    if (!worker.mcp_supported) worker.mcp_server_ids = [];
    if (!worker.skill_supported) worker.skill_ids = [];
  }

  function addProvider() {
    form.providers.push(blankProvider());
  }

  function removeProvider(index: number) {
    const [removed] = form.providers.splice(index, 1);
    if (!removed?.id) return;
    for (const worker of form.workers) {
      if (worker.provider_id === removed.id) worker.provider_id = '';
    }
  }

  function setProviderId(provider: ProviderSettings, nextId: string) {
    const previousId = provider.id;
    const normalizedNextId = nextId.trim();
    provider.id = normalizedNextId;
    if (previousId === normalizedNextId) return;
    for (const worker of form.workers) {
      if (worker.provider_id === previousId) worker.provider_id = normalizedNextId;
    }
  }

  function addMcpServer() {
    form.mcp_servers.push(blankMcpServer());
  }

  function removeMcpServer(index: number) {
    const [removed] = form.mcp_servers.splice(index, 1);
    if (!removed?.id) return;
    for (const worker of form.workers) {
      worker.mcp_server_ids = worker.mcp_server_ids.filter((id) => id !== removed.id);
    }
  }

  function addSkill() {
    form.skills.push(blankSkill());
  }

  function removeSkill(index: number) {
    const [removed] = form.skills.splice(index, 1);
    if (!removed?.id) return;
    for (const worker of form.workers) {
      worker.skill_ids = worker.skill_ids.filter((id) => id !== removed.id);
    }
  }

  function selectedProviderForWorker(worker: EditableWorkerSettings) {
    return form.providers.find((provider) => provider.id === worker.provider_id) || null;
  }

  function providersForWorker(worker: EditableWorkerSettings) {
    if (worker.type === 'mock') return [];
    return form.providers;
  }

  function providerWorkerCount(providerId: string) {
    return form.workers.filter((worker) => worker.provider_id === providerId).length;
  }

  function providerWorkerNames(providerId: string) {
    return form.workers
      .filter((worker) => worker.provider_id === providerId)
      .map((worker) => worker.name || '未命名 Worker');
  }

  function providerIdCount(providerId: string) {
    const normalizedProviderId = providerId.trim();
    if (!normalizedProviderId) return 0;
    return form.providers.filter((provider) => provider.id === normalizedProviderId).length;
  }

  function providerIssues(provider: ProviderSettings) {
    const issues: string[] = [];
    if (!provider.id.trim()) issues.push('Provider 标识不能为空');
    if (providerIdCount(provider.id) > 1) issues.push('Provider 标识重复');
    return issues;
  }

  function providerBindingIssue(worker: EditableWorkerSettings) {
    if (!worker.provider_id) return '';
    const provider = selectedProviderForWorker(worker);
    if (!provider) return `绑定的 Provider 不存在：${worker.provider_id}`;
    return '';
  }

  function validateProviderBindings() {
    const emptyProvider = form.providers.find((provider) => !provider.id.trim());
    if (emptyProvider) return 'Provider 标识不能为空';
    const duplicateProvider = form.providers.find((provider) => providerIdCount(provider.id) > 1);
    if (duplicateProvider) return `Provider 标识重复：${duplicateProvider.id}`;
    const conflictedWorker = form.workers.find((worker) => providerBindingIssue(worker));
    if (conflictedWorker) return `${conflictedWorker.name || '未命名 Worker'}：${providerBindingIssue(conflictedWorker)}`;
    return '';
  }

  function toggleWorkerMcp(worker: EditableWorkerSettings, serverId: string) {
    const next = new Set(worker.mcp_server_ids || []);
    if (next.has(serverId)) next.delete(serverId);
    else next.add(serverId);
    worker.mcp_server_ids = [...next];
  }

  function toggleWorkerSkill(worker: EditableWorkerSettings, skillId: string) {
    const next = new Set(worker.skill_ids || []);
    if (next.has(skillId)) next.delete(skillId);
    else next.add(skillId);
    worker.skill_ids = [...next];
  }

  function toggleWorkerTask(worker: EditableWorkerSettings, taskType: TaskType) {
    const next = new Set(worker.task_types || []);
    if (next.has(taskType)) {
      if (next.size === 1) return;
      next.delete(taskType);
    } else {
      next.add(taskType);
    }
    worker.task_types = TASK_ORDER.filter((task) => next.has(task));
  }

  function envEntries(env: Record<string, string>) {
    return Object.entries(sanitizeExtraEnv(env)).map(([key, value]) => ({ key, value }));
  }

  function addEnv(target: { extra_env?: Record<string, string>; env?: Record<string, string> }, field: 'extra_env' | 'env') {
    const env = { ...(target[field] || {}) };
    let index = 1;
    let candidate = `EXTRA_ENV_${index}`;
    while (Object.prototype.hasOwnProperty.call(env, candidate)) {
      index += 1;
      candidate = `EXTRA_ENV_${index}`;
    }
    env[candidate] = '';
    target[field] = env;
  }

  function updateEnvKey(target: { extra_env?: Record<string, string>; env?: Record<string, string> }, field: 'extra_env' | 'env', oldKey: string, nextKey: string) {
    const trimmed = nextKey.trim();
    const env = { ...(target[field] || {}) };
    if (!trimmed || trimmed === oldKey) return;
    const value = env[oldKey] || '';
    delete env[oldKey];
    env[trimmed] = value;
    target[field] = env;
  }

  function updateEnvValue(target: { extra_env?: Record<string, string>; env?: Record<string, string> }, field: 'extra_env' | 'env', key: string, value: string) {
    target[field] = { ...(target[field] || {}), [key]: value };
  }

  function removeEnv(target: { extra_env?: Record<string, string>; env?: Record<string, string> }, field: 'extra_env' | 'env', key: string) {
    const env = { ...(target[field] || {}) };
    delete env[key];
    target[field] = env;
  }

  function addMcpArg(server: McpServerSettings) {
    server.args = [...(server.args || []), ''];
  }

  function updateMcpArg(server: McpServerSettings, index: number, value: string) {
    const args = [...(server.args || [])];
    args[index] = value;
    server.args = args;
  }

  function removeMcpArg(server: McpServerSettings, index: number) {
    server.args = (server.args || []).filter((_, itemIndex) => itemIndex !== index);
  }

  async function syncResources() {
    await loadDispatchSettings(mode.value);
  }

  async function discoverSkills() {
    try {
      discoveredSkills.value = await api.discoverSkills(mode.value);
      ui.showToast('Skill 扫描完成', 'success');
    } catch (error) {
      ui.showToast(error instanceof Error ? error.message : String(error), 'error');
    }
  }

  async function importSkillZip(filename: string, contentBase64: string) {
    try {
      const result = await api.importSkillZip({
        mode: mode.value,
        filename,
        content_base64: contentBase64,
      });
      discoveredSkills.value = result.discovered;
      ui.showToast('Skill 已导入', 'success');
    } catch (error) {
      ui.showToast(error instanceof Error ? error.message : String(error), 'error');
    }
  }

  function registerDiscoveredSkill(skill: SkillSettings | import('@/types/dispatch').DiscoveredSkill) {
    if (form.skills.some((item) => item.id === skill.id)) return;
    form.skills.push(normalizeSkill({
      id: skill.id,
      name: skill.name,
      path: skill.path,
      description: 'description' in skill ? skill.description : '',
      enabled: true,
      enabled_claude: true,
      enabled_codex: true,
    }));
  }

  return {
    TASK_ORDER,
    leaseSettings,
    form,
    mode,
    meta,
    loadError,
    isLoading,
    isSaving,
    discoveredSkills,
    enabledWorkerCount,
    enabledProviderCount,
    enabledMcpCount,
    enabledSkillCount,
    loadLeaseSettings,
    saveLeaseSettings,
    loadDispatchSettings,
    setMode,
    saveDispatchSettings,
    testWorkerHealthcheck,
    addWorker,
    removeWorker,
    toggleWorkerEnabled,
    onWorkerTypeChange,
    addProvider,
    removeProvider,
    setProviderId,
    addMcpServer,
    removeMcpServer,
    addSkill,
    removeSkill,
    selectedProviderForWorker,
    providersForWorker,
    providerWorkerCount,
    providerWorkerNames,
    providerIssues,
    providerBindingIssue,
    validateProviderBindings,
    toggleWorkerMcp,
    toggleWorkerSkill,
    toggleWorkerTask,
    envEntries,
    addEnv,
    updateEnvKey,
    updateEnvValue,
    removeEnv,
    addMcpArg,
    updateMcpArg,
    removeMcpArg,
    syncResources,
    discoverSkills,
    importSkillZip,
    registerDiscoveredSkill,
  };
});
