<script setup lang="ts">
import { ChevronDown, ChevronRight, FlaskConical, Plus, RefreshCw, Save, Trash2 } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import FormField from '@/components/ui/FormField.vue';
import SelectInput from '@/components/ui/SelectInput.vue';
import TextInput from '@/components/ui/TextInput.vue';
import { useDispatchSettingsStore } from '@/stores/dispatchSettings';
import type { EditableWorkerSettings, TaskType, WorkerType } from '@/types/dispatch';

const store = useDispatchSettingsStore();
const taskTypes: TaskType[] = ['bootstrap', 'reason', 'explore', 'observe'];

function workerTypeTone(type: WorkerType) {
  if (type === 'claudecode') return 'sky';
  if (type === 'codex') return 'brand';
  if (type === 'pi') return 'amber';
  return 'slate';
}

function taskLabel(task: TaskType) {
  return {
    bootstrap: '启动',
    reason: '推理',
    explore: '探索',
    observe: '观察',
  }[task];
}

function hasWorkerDirectConfig(worker: EditableWorkerSettings) {
  return Boolean(
    worker.base_url
      || worker.has_auth_token
      || worker.auth_token,
  );
}

function workerEnvCount(worker: EditableWorkerSettings) {
  return store.envEntries(worker.extra_env).length;
}

function workerBindingSummary(worker: EditableWorkerSettings) {
  const provider = store.selectedProviderForWorker(worker);
  const enabledMcpIds = new Set(store.form.mcp_servers.filter((server) => server.enabled !== false).map((server) => server.id));
  const enabledSkillIds = new Set(store.form.skills.filter((skill) => skill.enabled !== false).map((skill) => skill.id));
  const selectedMcpIds = Array.isArray(worker.mcp_server_ids) ? worker.mcp_server_ids : [];
  const selectedSkillIds = Array.isArray(worker.skill_ids) ? worker.skill_ids : [];
  const activeMcpCount = selectedMcpIds.filter((id) => enabledMcpIds.has(id)).length;
  const activeSkillCount = selectedSkillIds.filter((id) => enabledSkillIds.has(id)).length;
  const providerLabel = provider ? provider.name || provider.id : '';

  return {
    provider: provider ? '已绑定 Provider' : '未绑定 Provider',
    providerDetail: provider
      ? `${providerLabel}${provider.enabled === false ? '（当前已禁用）' : ''}`
      : worker.type === 'mock'
        ? 'Mock 不需要 Provider'
        : hasWorkerDirectConfig(worker)
          ? '使用直连兼容配置'
          : '建议绑定 Provider',
    mcp: worker.mcp_supported ? `${selectedMcpIds.length} 个已选` : '当前未接入',
    mcpDetail: worker.mcp_supported
      ? selectedMcpIds.length
        ? `${activeMcpCount} 个启用，${Math.max(selectedMcpIds.length - activeMcpCount, 0)} 个未启用`
        : '还没有绑定 MCP'
      : worker.type === 'pi'
        ? 'Pi 暂时只保留展示入口'
        : '当前类型未实现 MCP 注入',
    skill: worker.skill_supported ? `${selectedSkillIds.length} 个已选` : '当前未接入',
    skillDetail: worker.skill_supported
      ? selectedSkillIds.length
        ? `${activeSkillCount} 个已对当前客户端启用，${Math.max(selectedSkillIds.length - activeSkillCount, 0)} 个未启用`
        : '还没有为当前客户端启用 Skill'
      : worker.type === 'pi'
        ? 'Pi 先标记为预留态'
        : '当前类型暂未接入 Skill 同步',
  };
}
</script>

<template>
  <section class="overflow-hidden rounded-3xl border border-slate-200/70 bg-white shadow-sm">
    <div class="border-b border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div class="min-w-0">
          <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Agent</div>
          <h3 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">Worker 池</h3>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            选择 Cairn 可使用的 Agent，绑定 Provider，并调整任务覆盖范围与优先级。
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <AppButton :icon="RefreshCw" @click="store.loadDispatchSettings()">重新加载</AppButton>
          <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
            {{ store.isSaving ? '保存中...' : '保存 Worker 配置' }}
          </AppButton>
          <AppButton variant="brand" :icon="Plus" @click="store.addWorker()">新增 Worker</AppButton>
        </div>
      </div>

      <div v-if="store.loadError" class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {{ store.loadError }}
      </div>
    </div>

    <div class="space-y-5 px-5 py-5 lg:px-8">
      <article
        v-for="(worker, idx) in store.form.workers"
        :key="worker.source_name || `${worker.type}-${idx}`"
        class="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm transition"
        :class="worker.enabled === false ? 'opacity-60' : ''"
      >
        <div class="border-b border-slate-200/80 bg-slate-50/80 px-4 py-4 lg:px-6">
          <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div class="min-w-0 space-y-3">
              <div class="flex flex-wrap items-center gap-2">
                <BadgePill :tone="workerTypeTone(worker.type)">{{ worker.type }}</BadgePill>
                <BadgePill :tone="worker.enabled ? 'teal' : 'slate'">{{ worker.enabled ? '启用中' : '已禁用' }}</BadgePill>
                <span class="text-xs text-slate-400">
                  {{ worker.source_name && worker.source_name !== worker.name ? `来自 ${worker.source_name}` : '新 Worker' }}
                </span>
              </div>
              <div class="min-w-0">
                <div class="truncate text-base font-semibold text-slate-900">{{ worker.name || '未命名 Worker' }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ workerBindingSummary(worker).providerDetail }}</div>
              </div>
            </div>
            <div class="flex shrink-0 flex-wrap items-center gap-2">
              <AppButton
                size="sm"
                :icon="FlaskConical"
                :disabled="worker.is_testing_healthcheck || worker.type === 'mock'"
                @click="store.testWorkerHealthcheck(worker)"
              >
                {{ worker.is_testing_healthcheck ? '测试中...' : '测试模型' }}
              </AppButton>
              <AppButton size="sm" :variant="worker.enabled ? 'secondary' : 'brand'" @click="store.toggleWorkerEnabled(worker)">
                {{ worker.enabled ? '禁用' : '启用' }}
              </AppButton>
              <AppButton size="sm" variant="danger" :icon="Trash2" @click="store.removeWorker(idx)">移除</AppButton>
            </div>
          </div>
        </div>

        <div class="px-4 py-5 lg:px-6">
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-12">
            <FormField label="Worker 名称" class="xl:col-span-3">
              <TextInput v-model="worker.name" />
            </FormField>
            <FormField label="类型" class="xl:col-span-2">
              <SelectInput v-model="worker.type" @change="store.onWorkerTypeChange(worker)">
                <option value="claudecode">Claude Code</option>
                <option value="codex">Codex</option>
                <option value="pi">Pi</option>
                <option value="mock">Mock</option>
              </SelectInput>
            </FormField>
            <FormField label="Provider 绑定" class="xl:col-span-3">
              <SelectInput v-model="worker.provider_id" :disabled="worker.provider_supported === false || worker.type === 'mock'">
                <option value="">未绑定</option>
                <option v-for="(provider, providerIndex) in store.providersForWorker(worker)" :key="providerIndex" :value="provider.id">
                  {{ provider.name || provider.id }}
                </option>
              </SelectInput>
              <p v-if="store.providerBindingIssue(worker)" class="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">
                {{ store.providerBindingIssue(worker) }}
              </p>
            </FormField>
            <FormField label="模型" class="xl:col-span-3">
              <TextInput v-model="worker.model" :disabled="worker.type === 'mock'" />
            </FormField>
            <FormField label="并发上限" class="xl:col-span-2">
              <TextInput v-model="worker.max_running" type="number" />
            </FormField>
            <FormField label="优先级" class="xl:col-span-2">
              <TextInput v-model="worker.priority" type="number" />
            </FormField>
          </div>

          <div v-if="worker.type === 'pi'" class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            <FormField label="Pi Provider API">
              <TextInput v-model="worker.provider_api" />
            </FormField>
            <FormField label="Pi 上下文窗口">
              <TextInput v-model="worker.context_window" type="number" />
            </FormField>
          </div>

          <div class="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/80">
            <div class="grid grid-cols-1 divide-y divide-slate-200 md:grid-cols-3 md:divide-x md:divide-y-0">
              <div class="px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Provider 状态</div>
                <div class="mt-1 text-sm font-medium text-slate-800">{{ workerBindingSummary(worker).provider }}</div>
                <div class="mt-1 text-xs leading-5 text-slate-500">{{ workerBindingSummary(worker).providerDetail }}</div>
              </div>
              <div class="px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">MCP 绑定</div>
                <div class="mt-1 text-sm font-medium text-slate-800">{{ workerBindingSummary(worker).mcp }}</div>
                <div class="mt-1 text-xs leading-5 text-slate-500">{{ workerBindingSummary(worker).mcpDetail }}</div>
              </div>
              <div class="px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">客户端启用</div>
                <div class="mt-1 text-sm font-medium text-slate-800">{{ workerBindingSummary(worker).skill }}</div>
                <div class="mt-1 text-xs leading-5 text-slate-500">{{ workerBindingSummary(worker).skillDetail }}</div>
              </div>
            </div>
          </div>

          <div
            v-if="worker.healthcheck"
            class="mt-5 rounded-2xl border px-4 py-3"
            :class="worker.healthcheck.ok ? 'border-emerald-200 bg-emerald-50/70' : 'border-rose-200 bg-rose-50/70'"
          >
            <div class="flex flex-wrap items-center gap-2">
              <BadgePill :tone="worker.healthcheck.ok ? 'teal' : 'rose'">
                {{ worker.healthcheck.ok ? '连通成功' : '连通失败' }}
              </BadgePill>
              <span class="text-xs text-slate-500">耗时 {{ worker.healthcheck.duration_ms || 0 }} ms</span>
              <span v-if="worker.healthcheck.http_status" class="text-xs text-slate-500">HTTP {{ worker.healthcheck.http_status }}</span>
              <span class="text-xs text-slate-500">退出码 {{ worker.healthcheck.returncode }}</span>
            </div>
            <div v-if="worker.healthcheck.command" class="mt-3">
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">测试命令</div>
              <pre class="mt-1 overflow-x-auto rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-[11px] leading-5 text-slate-600">{{ worker.healthcheck.command }}</pre>
            </div>
            <div v-if="worker.healthcheck.response_preview" class="mt-3">
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">响应预览</div>
              <div class="mt-1 break-all rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-xs leading-5 text-slate-700">
                {{ worker.healthcheck.response_preview }}
              </div>
            </div>
            <div v-if="worker.healthcheck.stderr_preview" class="mt-3">
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">错误预览</div>
              <div class="mt-1 break-all rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-xs leading-5 text-slate-700">
                {{ worker.healthcheck.stderr_preview }}
              </div>
            </div>
          </div>

          <div v-if="worker.type !== 'mock'" class="mt-5 border-t border-slate-200 pt-5">
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">配置来源</div>
                <p class="mt-1 text-xs leading-5 text-slate-500">
                  <template v-if="store.selectedProviderForWorker(worker)">
                    当前 Worker 使用自己的 Agent 类型和模型名称，Base URL 与鉴权来自绑定的 Provider。
                  </template>
                  <template v-else-if="worker.provider_id">
                    当前绑定关系异常，请重新选择 Provider。
                  </template>
                  <template v-else>
                    当前没有绑定 Provider。推荐先在 Provider 面板维护模型源，再回到这里选择。
                  </template>
                </p>
              </div>
            </div>

            <div v-if="store.selectedProviderForWorker(worker)" class="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-slate-50/80">
              <div class="grid grid-cols-1 divide-y divide-slate-200 md:grid-cols-[minmax(0,0.9fr)_minmax(0,0.9fr)_minmax(0,1.2fr)_minmax(0,0.8fr)] md:divide-x md:divide-y-0">
                <div class="px-4 py-3">
                  <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Provider</div>
                  <div class="mt-1 text-sm font-medium text-slate-800">
                    {{ store.selectedProviderForWorker(worker)?.name || store.selectedProviderForWorker(worker)?.id }}
                  </div>
                  <div class="mt-1 break-all text-xs text-slate-500">{{ store.selectedProviderForWorker(worker)?.id }}</div>
                </div>
                <div class="px-4 py-3">
                  <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Worker 模型</div>
                  <div class="mt-1 break-all text-sm font-medium text-slate-800">
                    {{ worker.model || '未设置' }}
                  </div>
                </div>
                <div class="px-4 py-3">
                  <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Provider Base URL</div>
                  <div class="mt-1 break-all text-sm font-medium text-slate-800">
                    {{ store.selectedProviderForWorker(worker)?.base_url || '未设置' }}
                  </div>
                </div>
                <div class="px-4 py-3">
                  <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">鉴权</div>
                  <div class="mt-1 text-sm font-medium text-slate-800">
                    {{ store.selectedProviderForWorker(worker)?.has_auth_token ? 'Provider 已保存' : 'Provider 未保存' }}
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="mt-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
              <template v-if="worker.provider_id">
                当前 Provider 绑定无效，不会保存为可用配置。请在上方重新选择 Provider，或清空绑定后使用 Worker 直连字段。
              </template>
              <template v-else>
                Worker 直连端点和 Key 只用于旧 YAML 迁移或临时测试；常规使用请选择一个 Provider。
              </template>
              <div v-if="!worker.provider_id" class="mt-3">
                <AppButton
                  size="sm"
                  :icon="worker.show_direct_config ? ChevronDown : ChevronRight"
                  @click="worker.show_direct_config = !worker.show_direct_config"
                >
                  {{ worker.show_direct_config ? '收起直连端点' : '展开直连端点' }}
                </AppButton>
              </div>
            </div>

            <div
              v-if="!worker.provider_id && worker.show_direct_config"
              class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
            >
              <FormField label="直连 Base URL">
                <TextInput v-model="worker.base_url" />
              </FormField>
              <FormField label="直连 API Key / Token" :hint="worker.has_auth_token ? '已存在 key，留空会保持不变。' : '这个 Worker 还没有保存 key。'">
                <TextInput v-model="worker.auth_token" placeholder="留空则保留现有 key" />
              </FormField>
            </div>
          </div>

          <div class="mt-5 grid grid-cols-1 gap-5 border-t border-slate-200 pt-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
            <div class="min-w-0">
              <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Worker 高级环境</div>
                  <p class="mt-1 text-xs leading-5 text-slate-500">只放 Worker 进程专用变量；模型使用上方主字段，Base URL 和 Key 放在 Provider。</p>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                  <BadgePill :tone="workerEnvCount(worker) ? 'brand' : 'slate'">
                    {{ workerEnvCount(worker) }} 个变量
                  </BadgePill>
                  <AppButton
                    size="sm"
                    :icon="worker.show_runtime_env ? ChevronDown : ChevronRight"
                    @click="worker.show_runtime_env = !worker.show_runtime_env"
                  >
                    {{ worker.show_runtime_env ? '收起' : '展开' }}
                  </AppButton>
                  <AppButton v-if="worker.show_runtime_env" size="sm" :icon="Plus" @click="store.addEnv(worker, 'extra_env')">新增变量</AppButton>
                </div>
              </div>
              <div v-if="worker.show_runtime_env" class="mt-3 space-y-2">
                <div
                  v-for="(row, envIndex) in store.envEntries(worker.extra_env)"
                  :key="`${row.key}-${envIndex}`"
                  class="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto]"
                >
                  <input
                    :value="row.key"
                    placeholder="KEY"
                    class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                    @input="store.updateEnvKey(worker, 'extra_env', row.key, ($event.target as HTMLInputElement).value)"
                  />
                  <input
                    :value="row.value"
                    placeholder="VALUE"
                    class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                    @input="store.updateEnvValue(worker, 'extra_env', row.key, ($event.target as HTMLInputElement).value)"
                  />
                  <AppButton size="sm" variant="danger" @click="store.removeEnv(worker, 'extra_env', row.key)">删除</AppButton>
                </div>
                <div v-if="workerEnvCount(worker) === 0" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-400">
                  当前没有 Worker 专用环境变量。
                </div>
              </div>
            </div>

            <div class="min-w-0 space-y-5">
              <div>
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">能力绑定</div>
                <div class="mt-3 space-y-4">
                  <div>
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-sm font-medium text-slate-700">MCP</span>
                      <BadgePill :tone="worker.mcp_supported ? 'teal' : 'slate'">{{ worker.mcp_supported ? '已接入' : '未接入' }}</BadgePill>
                    </div>
                    <div v-if="worker.mcp_supported" class="mt-2 flex flex-wrap gap-2">
                      <button
                        v-for="server in store.form.mcp_servers"
                        :key="server.id"
                        type="button"
                        class="rounded-full border px-3 py-1.5 text-xs font-medium transition"
                        :class="worker.mcp_server_ids.includes(server.id) ? 'border-brand-200 bg-brand-50 text-brand-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'"
                        @click="store.toggleWorkerMcp(worker, server.id)"
                      >
                        {{ server.name || server.id }}
                      </button>
                    </div>
                    <p v-if="worker.mcp_supported && store.form.mcp_servers.length === 0" class="mt-2 text-xs text-slate-400">还没有配置 MCP 资源。</p>
                    <p v-if="!worker.mcp_supported" class="mt-2 text-xs text-slate-400">
                      {{ worker.type === 'pi' ? 'Pi 暂未接入 MCP 注入，当前先作为预留能力展示。' : '当前 Worker 类型暂不支持 MCP 注入。' }}
                    </p>
                  </div>

                  <div>
                    <div class="flex items-center justify-between gap-2">
                      <span class="text-sm font-medium text-slate-700">Skill</span>
                      <BadgePill :tone="worker.skill_supported ? 'teal' : 'slate'">{{ worker.skill_supported ? '已接入' : '预留中' }}</BadgePill>
                    </div>
                    <div v-if="worker.skill_supported" class="mt-2 flex flex-wrap gap-2">
                      <button
                        v-for="skill in store.form.skills"
                        :key="skill.id"
                        type="button"
                        class="rounded-full border px-3 py-1.5 text-xs font-medium transition"
                        :class="worker.skill_ids.includes(skill.id) ? 'border-brand-200 bg-brand-50 text-brand-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'"
                        @click="store.toggleWorkerSkill(worker, skill.id)"
                      >
                        {{ skill.name || skill.id }}
                      </button>
                    </div>
                    <p v-if="worker.skill_supported && store.form.skills.length === 0" class="mt-2 text-xs text-slate-400">还没有注册 Skill。</p>
                    <p v-if="!worker.skill_supported" class="mt-2 text-xs text-slate-400">
                      {{ worker.type === 'pi' ? 'Pi 当前明确标记为 Skill 预留态，暂不自动注入。' : '当前 Worker 类型暂未接入 Skill 同步。' }}
                    </p>
                  </div>
                </div>
              </div>

              <div class="border-t border-slate-200 pt-5">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">任务覆盖</div>
                <div class="mt-2 flex flex-wrap gap-2">
                  <button
                    v-for="taskType in taskTypes"
                    :key="taskType"
                    type="button"
                    class="rounded-full border px-3 py-1.5 text-xs font-medium transition"
                    :class="worker.task_types.includes(taskType) ? 'border-brand-200 bg-brand-50 text-brand-700' : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'"
                    @click="store.toggleWorkerTask(worker, taskType)"
                  >
                    {{ taskLabel(taskType) }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </article>

      <EmptyState
        v-if="store.form.workers.length === 0"
        title="还没有配置 Worker"
        detail="新增 Worker 后，调度器就可以选择它。"
      />
    </div>

    <div class="border-t border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col justify-between gap-4 rounded-[24px] border border-slate-200 bg-slate-50/80 px-5 py-4 lg:flex-row lg:items-center">
        <div>
          <div class="text-sm font-medium text-slate-800">
            {{ store.mode === 'ui' ? '保存后会写入 UI 真源并重新编译 dispatch_ui.yaml。' : '保存后会更新当前 YAML 配置。' }}
          </div>
          <p class="mt-1 text-xs text-slate-400">
            {{ store.meta.writable ? '已启动的 Agent 继续使用旧配置，新任务会自动读取最新 Worker 设置。' : '当前配置源只读，暂时无法保存。' }}
          </p>
        </div>
        <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
          {{ store.isSaving ? '保存中...' : '保存 Worker 配置' }}
        </AppButton>
      </div>
    </div>
  </section>
</template>
