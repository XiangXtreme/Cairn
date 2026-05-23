<script setup lang="ts">
import { reactive } from 'vue';
import { AlertTriangle, ChevronDown, ChevronRight, Plus, RefreshCw, Save, Trash2 } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import FormField from '@/components/ui/FormField.vue';
import TextInput from '@/components/ui/TextInput.vue';
import { useDispatchSettingsStore } from '@/stores/dispatchSettings';
import type { ProviderSettings } from '@/types/dispatch';

const store = useDispatchSettingsStore();
const expandedProviderEnv = reactive<Record<number, boolean>>({});

function providerEnvCount(provider: ProviderSettings) {
  return store.envEntries(provider.extra_env).length;
}
</script>

<template>
  <section class="overflow-hidden rounded-3xl border border-slate-200/70 bg-white shadow-sm">
    <div class="border-b border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div class="min-w-0">
          <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Provider</div>
          <h3 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">统一 Provider 资源</h3>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Provider 只维护服务端点、鉴权和共享环境变量；具体 Agent 类型和模型名称在 Worker 中指定。
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <AppButton :icon="RefreshCw" @click="store.loadDispatchSettings()">重新加载</AppButton>
          <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
            {{ store.isSaving ? '保存中...' : '保存 Provider 配置' }}
          </AppButton>
          <AppButton variant="brand" :icon="Plus" @click="store.addProvider()">新增 Provider</AppButton>
        </div>
      </div>
    </div>

    <div class="space-y-4 px-5 py-5 lg:px-8">
      <article
        v-for="(provider, idx) in store.form.providers"
        :key="idx"
        class="rounded-[28px] border border-slate-200 bg-white shadow-sm"
      >
        <div class="flex flex-col gap-4 border-b border-slate-200/80 bg-slate-50/80 px-4 py-4 lg:px-6 xl:flex-row xl:items-start xl:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <BadgePill :tone="provider.enabled ? 'teal' : 'slate'">{{ provider.enabled ? '启用中' : '已禁用' }}</BadgePill>
              <BadgePill :tone="provider.has_auth_token ? 'brand' : 'slate'">{{ provider.has_auth_token ? '已存鉴权' : '未存鉴权' }}</BadgePill>
            </div>
            <div class="mt-3 text-base font-semibold text-slate-900">{{ provider.name || provider.id || '未命名 Provider' }}</div>
            <div class="mt-1 text-xs text-slate-500">{{ store.providerWorkerCount(provider.id) }} 个 Worker 绑定</div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <AppButton size="sm" :variant="provider.enabled ? 'secondary' : 'brand'" @click="provider.enabled = !provider.enabled">
              {{ provider.enabled ? '禁用' : '启用' }}
            </AppButton>
            <AppButton size="sm" variant="danger" :icon="Trash2" @click="store.removeProvider(idx)">移除</AppButton>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 px-4 py-5 lg:px-6 md:grid-cols-2 xl:grid-cols-3">
          <FormField label="标识">
            <TextInput
              :model-value="provider.id"
              @update:model-value="store.setProviderId(provider, String($event ?? ''))"
            />
          </FormField>
          <FormField label="名称">
            <TextInput v-model="provider.name" />
          </FormField>
          <FormField label="Base URL">
            <TextInput v-model="provider.base_url" />
          </FormField>
          <FormField label="API Key / Token" :hint="provider.has_auth_token ? '已存在 key，留空会保持不变。' : '这个 Provider 还没有保存 key。'">
            <TextInput v-model="provider.auth_token" placeholder="留空则保留现有 key" />
          </FormField>
        </div>

        <div class="border-t border-slate-200 px-4 py-4 lg:px-6">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Provider 高级环境</div>
              <p class="mt-1 text-xs leading-5 text-slate-500">
                只放账号或服务端点共享的附加变量；模型名称和 Agent 参数放在 Worker。
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <BadgePill :tone="providerEnvCount(provider) ? 'brand' : 'slate'">
                {{ providerEnvCount(provider) }} 个变量
              </BadgePill>
              <AppButton
                size="sm"
                :icon="expandedProviderEnv[idx] ? ChevronDown : ChevronRight"
                @click="expandedProviderEnv[idx] = !expandedProviderEnv[idx]"
              >
                {{ expandedProviderEnv[idx] ? '收起' : '展开' }}
              </AppButton>
              <AppButton v-if="expandedProviderEnv[idx]" size="sm" :icon="Plus" @click="store.addEnv(provider, 'extra_env')">新增变量</AppButton>
            </div>
          </div>

          <div v-if="expandedProviderEnv[idx]" class="mt-3 space-y-2">
            <div
              v-for="(row, envIndex) in store.envEntries(provider.extra_env)"
              :key="`${row.key}-${envIndex}`"
              class="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto]"
            >
              <input
                :value="row.key"
                placeholder="KEY"
                class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                @input="store.updateEnvKey(provider, 'extra_env', row.key, ($event.target as HTMLInputElement).value)"
              />
              <input
                :value="row.value"
                placeholder="VALUE"
                class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                @input="store.updateEnvValue(provider, 'extra_env', row.key, ($event.target as HTMLInputElement).value)"
              />
              <AppButton size="sm" variant="danger" @click="store.removeEnv(provider, 'extra_env', row.key)">删除</AppButton>
            </div>
            <div v-if="providerEnvCount(provider) === 0" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-400">
              当前没有 Provider 附加环境变量。
            </div>
          </div>
        </div>

        <div class="border-t border-slate-200 px-4 py-4 lg:px-6">
          <div v-if="store.providerIssues(provider).length" class="mb-3 space-y-2">
            <div
              v-for="issue in store.providerIssues(provider)"
              :key="issue"
              class="flex items-start gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900"
            >
              <AlertTriangle class="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{{ issue }}</span>
            </div>
          </div>
          <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">绑定 Worker</div>
              <p class="mt-1 text-xs leading-5 text-slate-500">
                修改 Provider 标识时，已绑定 Worker 会同步迁移到新标识。
              </p>
            </div>
            <div class="flex flex-wrap gap-2 sm:justify-end">
              <BadgePill
                v-for="workerName in store.providerWorkerNames(provider.id)"
                :key="workerName"
                tone="brand"
              >
                {{ workerName }}
              </BadgePill>
              <span v-if="store.providerWorkerNames(provider.id).length === 0" class="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-400">
                未绑定 Worker
              </span>
            </div>
          </div>
        </div>
      </article>

      <EmptyState
        v-if="store.form.providers.length === 0"
        title="还没有配置 Provider"
        detail="新增 Provider 后，Worker 可以绑定统一模型源。"
      />
    </div>

    <div class="border-t border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col justify-between gap-4 rounded-[24px] border border-slate-200 bg-slate-50/80 px-5 py-4 lg:flex-row lg:items-center">
        <div>
          <div class="text-sm font-medium text-slate-800">
            {{ store.mode === 'ui' ? '保存后会写入 UI 真源并重新编译 dispatch_ui.yaml。' : '保存后会更新当前 YAML 配置。' }}
          </div>
          <p class="mt-1 text-xs text-slate-400">
            {{ store.meta.writable ? 'Provider 会作为 Worker 的共享端点和鉴权来源。' : '当前配置源只读，暂时无法保存。' }}
          </p>
        </div>
        <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
          {{ store.isSaving ? '保存中...' : '保存 Provider 配置' }}
        </AppButton>
      </div>
    </div>
  </section>
</template>
