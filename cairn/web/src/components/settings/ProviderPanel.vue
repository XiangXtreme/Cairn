<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import FormField from '@/components/ui/FormField.vue';
import SelectInput from '@/components/ui/SelectInput.vue';
import TextInput from '@/components/ui/TextInput.vue';
import { useDispatchSettingsStore } from '@/stores/dispatchSettings';

const store = useDispatchSettingsStore();
</script>

<template>
  <section class="overflow-hidden rounded-3xl border border-slate-200/70 bg-white shadow-sm">
    <div class="border-b border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div class="min-w-0">
          <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Provider</div>
          <h3 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">统一 Provider 资源</h3>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            先维护模型源、Base URL、鉴权和附加环境变量，再由 Worker 绑定使用。
          </p>
        </div>
        <AppButton variant="primary" :icon="Plus" @click="store.addProvider()">新增 Provider</AppButton>
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
              <BadgePill tone="sky">{{ provider.kind }}</BadgePill>
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
            <TextInput v-model="provider.id" />
          </FormField>
          <FormField label="名称">
            <TextInput v-model="provider.name" />
          </FormField>
          <FormField label="类型">
            <SelectInput v-model="provider.kind" @change="store.onProviderKindChange(provider)">
              <option value="claudecode">Claude Code</option>
              <option value="codex">Codex</option>
              <option value="pi">Pi</option>
            </SelectInput>
          </FormField>
          <FormField label="模型">
            <TextInput v-model="provider.model" />
          </FormField>
          <FormField label="Base URL">
            <TextInput v-model="provider.base_url" />
          </FormField>
          <FormField label="API Key / Token" :hint="provider.has_auth_token ? '已存在 key，留空会保持不变。' : '这个 Provider 还没有保存 key。'">
            <TextInput v-model="provider.auth_token" placeholder="留空则保留现有 key" />
          </FormField>
          <template v-if="provider.kind === 'pi'">
            <FormField label="Provider API">
              <TextInput v-model="provider.provider_api" />
            </FormField>
            <FormField label="上下文窗口">
              <TextInput v-model="provider.context_window" type="number" />
            </FormField>
          </template>
        </div>
      </article>

      <EmptyState
        v-if="store.form.providers.length === 0"
        title="还没有配置 Provider"
        detail="新增 Provider 后，Worker 可以绑定统一模型源。"
      />
    </div>
  </section>
</template>
