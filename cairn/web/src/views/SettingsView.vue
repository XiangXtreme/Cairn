<script setup lang="ts">
import { ArrowLeft, Clock, Cpu, Database, RefreshCw, Save, Server, SlidersHorizontal, Wrench } from 'lucide-vue-next';
import { storeToRefs } from 'pinia';
import { onMounted } from 'vue';

import McpPanel from '@/components/settings/McpPanel.vue';
import ProviderPanel from '@/components/settings/ProviderPanel.vue';
import SkillPanel from '@/components/settings/SkillPanel.vue';
import WorkerPanel from '@/components/settings/WorkerPanel.vue';
import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import FormField from '@/components/ui/FormField.vue';
import TextInput from '@/components/ui/TextInput.vue';
import { useDispatchSettingsStore } from '@/stores/dispatchSettings';
import { useUiStore, type SettingsSection } from '@/stores/ui';

const store = useDispatchSettingsStore();
const ui = useUiStore();
const { settingsSection } = storeToRefs(ui);

const navItems: { id: SettingsSection; label: string; desc: string; icon: typeof Server }[] = [
  { id: 'mode', label: '运行模式', desc: '配置来源与热加载', icon: Database },
  { id: 'providers', label: 'Provider', desc: '端点与鉴权配置', icon: Server },
  { id: 'workers', label: 'Agent / Worker', desc: '模型与任务覆盖', icon: Cpu },
  { id: 'mcp', label: 'MCP', desc: '统一资源与绑定', icon: Wrench },
  { id: 'skills', label: 'Skill', desc: '本地 skill 注册', icon: Wrench },
  { id: 'runtime', label: '调度参数', desc: '并发与收敛策略', icon: SlidersHorizontal },
];

onMounted(async () => {
  await Promise.all([store.loadLeaseSettings(), store.loadDispatchSettings()]);
});

function backToWorkspace() {
  window.location.hash = '#/';
}

function formatTime(value: string | null | undefined) {
  if (!value) return '尚未编译';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="sticky top-0 z-30 border-b border-slate-200/80 bg-white/95 backdrop-blur">
      <div class="flex min-h-[88px] items-center justify-between gap-4 px-5 lg:px-8">
        <div class="flex min-w-0 items-center gap-3">
          <button
            type="button"
            class="inline-flex h-10 w-10 items-center justify-center rounded-2xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            @click="backToWorkspace"
          >
            <ArrowLeft class="h-5 w-5" aria-hidden="true" />
          </button>
          <div class="min-w-0">
            <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">工作区设置</div>
            <h1 class="mt-0.5 truncate text-xl font-semibold tracking-tight text-slate-900">调度器控制台</h1>
            <div class="mt-0.5 text-[10px] font-mono text-slate-400">vue settings-modernization-20260523</div>
          </div>
        </div>
        <div class="hidden min-w-0 items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-2 text-sm text-slate-500 md:flex">
          <span class="font-medium text-slate-700">{{ store.mode === 'ui' ? 'UI 配置' : '配置文件' }}</span>
          <span class="truncate">{{ store.meta.compiled_path || store.meta.path }}</span>
        </div>
      </div>
    </header>

    <main class="grid grid-cols-1 gap-6 px-4 py-5 lg:grid-cols-[320px_minmax(0,1fr)] lg:px-6 xl:px-8">
      <aside class="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm lg:sticky lg:top-[108px] lg:self-start">
        <div class="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">设置分区</div>
        <nav class="mt-1 space-y-1">
          <button
            v-for="item in navItems"
            :key="item.id"
            type="button"
            class="flex w-full items-start gap-3 rounded-2xl border px-3 py-3 text-left transition"
            :class="settingsSection === item.id ? 'border-brand-200 bg-brand-50/80 text-brand-900' : 'border-transparent text-slate-600 hover:bg-slate-50'"
            @click="ui.openSettingsSection(item.id)"
          >
            <component :is="item.icon" class="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <span class="min-w-0">
              <span class="block text-sm font-semibold">{{ item.label }}</span>
              <span class="mt-1 block text-[11px] leading-5" :class="settingsSection === item.id ? 'text-brand-700' : 'text-slate-400'">{{ item.desc }}</span>
            </span>
          </button>
        </nav>
      </aside>

      <div class="min-w-0 space-y-6">
        <section v-if="settingsSection === 'mode' || settingsSection === 'runtime'" class="grid grid-cols-1 gap-5 xl:grid-cols-[0.95fr_1.45fr]">
          <article v-if="settingsSection === 'mode'" class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">服务端</div>
                <h3 class="mt-1 text-lg font-semibold tracking-tight text-slate-900">租约超时</h3>
              </div>
              <BadgePill tone="teal">立即生效</BadgePill>
            </div>
            <div class="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField label="意图超时">
                <TextInput v-model="store.leaseSettings.intent_timeout" type="number" />
              </FormField>
              <FormField label="推理超时">
                <TextInput v-model="store.leaseSettings.reason_timeout" type="number" />
              </FormField>
            </div>
            <div class="mt-5 flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p class="text-xs leading-5 text-slate-500">这些值控制 Worker 在没有心跳时租约保留多久。</p>
              <AppButton :icon="Save" @click="store.saveLeaseSettings()">保存超时</AppButton>
            </div>
          </article>

          <article class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm" :class="settingsSection === 'runtime' ? 'xl:col-span-2' : ''">
            <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">调度器</div>
                <h3 class="mt-1 text-lg font-semibold tracking-tight text-slate-900">运行参数</h3>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <AppButton :variant="store.mode === 'file' ? 'primary' : 'secondary'" @click="store.setMode('file')">配置文件</AppButton>
                <AppButton :variant="store.mode === 'ui' ? 'primary' : 'secondary'" @click="store.setMode('ui')">UI 配置</AppButton>
                <AppButton :icon="RefreshCw" @click="store.loadDispatchSettings()">重新加载</AppButton>
              </div>
            </div>

            <div class="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div class="flex flex-wrap items-center gap-2">
                <BadgePill :tone="store.meta.writable ? 'teal' : 'rose'">{{ store.meta.writable ? '可写' : '只读' }}</BadgePill>
                <BadgePill :tone="store.meta.hot_reload_enabled ? 'teal' : 'amber'">{{ store.meta.hot_reload_enabled ? '热加载开启' : '热加载关闭' }}</BadgePill>
                <span class="text-xs text-slate-500">最近编译：{{ formatTime(store.meta.compiled_updated_at) }}</span>
              </div>
              <div class="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-500 xl:grid-cols-2">
                <div class="min-w-0">
                  <span class="text-slate-400">当前生效来源：</span>
                  <span class="break-all font-mono">{{ store.meta.source_path || store.meta.path }}</span>
                </div>
                <div class="min-w-0">
                  <span class="text-slate-400">编译产物：</span>
                  <span class="break-all font-mono">{{ store.meta.compiled_path || store.meta.path }}</span>
                </div>
              </div>
              <p v-if="store.meta.last_validation_error" class="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                {{ store.meta.last_validation_error }}
              </p>
            </div>

            <div class="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
              <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Worker</div>
                <div class="mt-1 text-lg font-semibold text-slate-900">{{ store.form.workers.length }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ store.enabledWorkerCount ? `${store.enabledWorkerCount} 个启用` : '暂无启用项' }}</div>
              </div>
              <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Provider</div>
                <div class="mt-1 text-lg font-semibold text-slate-900">{{ store.form.providers.length }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ store.enabledProviderCount ? `${store.enabledProviderCount} 个启用` : '暂无启用项' }}</div>
              </div>
              <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">MCP</div>
                <div class="mt-1 text-lg font-semibold text-slate-900">{{ store.form.mcp_servers.length }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ store.enabledMcpCount ? `${store.enabledMcpCount} 个启用` : '暂无启用项' }}</div>
              </div>
              <div class="rounded-2xl border border-slate-200 bg-white px-4 py-3">
                <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Skill</div>
                <div class="mt-1 text-lg font-semibold text-slate-900">{{ store.form.skills.length }}</div>
                <div class="mt-1 text-xs text-slate-500">{{ store.enabledSkillCount ? `${store.enabledSkillCount} 个启用` : '暂无启用项' }}</div>
              </div>
            </div>

            <div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <FormField label="最大 Worker">
                <TextInput v-model="store.form.runtime.max_workers" type="number" />
              </FormField>
              <FormField label="最大项目数">
                <TextInput v-model="store.form.runtime.max_running_projects" type="number" />
              </FormField>
              <FormField label="单项目上限">
                <TextInput v-model="store.form.runtime.max_project_workers" type="number" />
              </FormField>
              <FormField label="每轮意图数">
                <TextInput v-model="store.form.tasks.reason.max_intents" type="number" />
              </FormField>
              <FormField label="调度间隔">
                <TextInput v-model="store.form.runtime.interval" type="number" />
              </FormField>
              <FormField label="健康检查">
                <TextInput v-model="store.form.runtime.healthcheck_timeout" type="number" />
              </FormField>
              <FormField label="提示词组">
                <TextInput v-model="store.form.runtime.prompt_group" />
              </FormField>
              <FormField label="不可用阈值">
                <TextInput v-model="store.form.tasks.reason.unavailable_fact_limit" type="number" />
              </FormField>
            </div>

            <div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
              <FormField label="Observe 超时">
                <TextInput v-model="store.form.tasks.observe.timeout" type="number" />
              </FormField>
              <FormField label="Observe 间隔">
                <TextInput v-model="store.form.tasks.observe.min_interval_seconds" type="number" />
              </FormField>
              <FormField label="Recent Run 数">
                <TextInput v-model="store.form.tasks.observe.recent_run_limit" type="number" />
              </FormField>
              <FormField label="最大更新数">
                <TextInput v-model="store.form.tasks.observe.max_updates" type="number" />
              </FormField>
            </div>

            <div class="mt-5 grid grid-cols-1 gap-3 lg:grid-cols-2">
              <label class="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <span>
                  <span class="block text-sm font-medium text-slate-700">目标不可用时继续派发</span>
                  <span class="mt-0.5 block text-xs leading-5 text-slate-500">关闭后，连续不可用事实会让项目等待人工恢复。</span>
                </span>
                <input v-model="store.form.tasks.reason.allow_unavailable_dispatch" type="checkbox" class="h-5 w-5 rounded border-slate-300 text-brand-500 focus:ring-brand-200" />
              </label>
              <label class="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                <span>
                  <span class="block text-sm font-medium text-slate-700">Observer 调度</span>
                  <span class="mt-0.5 block text-xs leading-5 text-slate-500">启用后低优先级观察图谱和 worker run 摘要。</span>
                </span>
                <input v-model="store.form.tasks.observe.enabled" type="checkbox" class="h-5 w-5 rounded border-slate-300 text-brand-500 focus:ring-brand-200" />
              </label>
            </div>

            <div class="mt-5 flex justify-end">
              <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
                {{ store.isSaving ? '保存中...' : '保存调度配置' }}
              </AppButton>
            </div>
          </article>
        </section>

        <ProviderPanel v-if="settingsSection === 'providers'" />
        <WorkerPanel v-if="settingsSection === 'workers'" />
        <McpPanel v-if="settingsSection === 'mcp'" />
        <SkillPanel v-if="settingsSection === 'skills'" />
      </div>
    </main>
  </div>
</template>
