<script setup lang="ts">
import { Plus, RefreshCw, Save, Trash2 } from 'lucide-vue-next';

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
          <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">MCP</div>
          <h3 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">统一 MCP 注册与绑定</h3>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            在 Cairn 里维护中央 MCP 注册表，再由 Worker 绑定并注入到支持的客户端。
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <AppButton :icon="RefreshCw" @click="store.syncResources()">重新加载</AppButton>
          <AppButton variant="primary" :icon="Plus" @click="store.addMcpServer()">新增 MCP</AppButton>
        </div>
      </div>

      <div class="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">MCP</div>
          <div class="mt-1 text-lg font-semibold text-slate-900">{{ store.form.mcp_servers.length }}</div>
          <div class="mt-1 text-xs text-slate-500">{{ store.enabledMcpCount ? `${store.enabledMcpCount} 个启用` : '暂无启用项' }}</div>
        </div>
        <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">Worker</div>
          <div class="mt-1 text-lg font-semibold text-slate-900">{{ store.form.workers.length }}</div>
          <div class="mt-1 text-xs text-slate-500">可绑定资源</div>
        </div>
      </div>
    </div>

    <div class="space-y-4 px-5 py-5 lg:px-8">
      <article
        v-for="(server, idx) in store.form.mcp_servers"
        :key="idx"
        class="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm"
      >
        <div class="flex flex-col gap-4 border-b border-slate-200/80 bg-slate-50/80 px-4 py-4 lg:px-6 xl:flex-row xl:items-start xl:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <BadgePill tone="brand">{{ server.transport }}</BadgePill>
              <BadgePill :tone="server.enabled ? 'teal' : 'slate'">{{ server.enabled ? '启用中' : '已禁用' }}</BadgePill>
            </div>
            <div class="mt-3 truncate text-base font-semibold text-slate-900">{{ server.name || server.id || '未命名 MCP' }}</div>
            <div class="mt-1 break-all text-xs text-slate-500">{{ server.transport === 'stdio' ? server.command || '未设置命令' : server.url || '未设置 URL' }}</div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <AppButton size="sm" :variant="server.enabled ? 'secondary' : 'brand'" @click="server.enabled = !server.enabled">
              {{ server.enabled ? '禁用' : '启用' }}
            </AppButton>
            <AppButton size="sm" variant="danger" :icon="Trash2" @click="store.removeMcpServer(idx)">移除</AppButton>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 px-4 py-5 lg:px-6 md:grid-cols-2 xl:grid-cols-3">
          <FormField label="标识">
            <TextInput v-model="server.id" />
          </FormField>
          <FormField label="名称">
            <TextInput v-model="server.name" />
          </FormField>
          <FormField label="传输">
            <SelectInput v-model="server.transport">
              <option value="stdio">stdio</option>
              <option value="http">http</option>
            </SelectInput>
          </FormField>
          <FormField v-if="server.transport === 'stdio'" label="命令" class="xl:col-span-2">
            <TextInput v-model="server.command" />
          </FormField>
          <FormField v-else label="URL" class="xl:col-span-2">
            <TextInput v-model="server.url" />
          </FormField>
        </div>

        <div class="grid grid-cols-1 gap-5 border-t border-slate-200 px-4 py-5 lg:px-6 xl:grid-cols-2">
          <div class="min-w-0">
            <div class="flex items-center justify-between gap-3">
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">参数</div>
              <AppButton size="sm" :icon="Plus" @click="store.addMcpArg(server)">新增参数</AppButton>
            </div>
            <div class="mt-3 space-y-2">
              <div v-for="(arg, argIndex) in server.args" :key="argIndex" class="grid grid-cols-[minmax(0,1fr)_auto] gap-2">
                <input
                  :value="arg"
                  class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  placeholder="arg"
                  @input="store.updateMcpArg(server, argIndex, ($event.target as HTMLInputElement).value)"
                />
                <AppButton size="sm" variant="danger" @click="store.removeMcpArg(server, argIndex)">删除</AppButton>
              </div>
              <div v-if="server.args.length === 0" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-400">
                当前没有参数。
              </div>
            </div>
          </div>

          <div class="min-w-0">
            <div class="flex items-center justify-between gap-3">
              <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">环境变量</div>
              <AppButton size="sm" :icon="Plus" @click="store.addEnv(server, 'env')">新增变量</AppButton>
            </div>
            <div class="mt-3 space-y-2">
              <div
                v-for="(row, envIndex) in store.envEntries(server.env)"
                :key="`${row.key}-${envIndex}`"
                class="grid grid-cols-1 gap-2 sm:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_auto]"
              >
                <input
                  :value="row.key"
                  placeholder="KEY"
                  class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  @input="store.updateEnvKey(server, 'env', row.key, ($event.target as HTMLInputElement).value)"
                />
                <input
                  :value="row.value"
                  placeholder="VALUE"
                  class="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
                  @input="store.updateEnvValue(server, 'env', row.key, ($event.target as HTMLInputElement).value)"
                />
                <AppButton size="sm" variant="danger" @click="store.removeEnv(server, 'env', row.key)">删除</AppButton>
              </div>
              <div v-if="store.envEntries(server.env).length === 0" class="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-xs text-slate-400">
                当前没有环境变量。
              </div>
            </div>
          </div>
        </div>
      </article>

      <EmptyState
        v-if="store.form.mcp_servers.length === 0"
        title="还没有配置 MCP"
        detail="新增 MCP 后，可以在 Worker 面板里绑定。"
      />
    </div>

    <div class="border-t border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col justify-between gap-4 rounded-[24px] border border-slate-200 bg-slate-50/80 px-5 py-4 lg:flex-row lg:items-center">
        <div>
          <div class="text-sm font-medium text-slate-800">保存后会同步到后续启动的支持型 Worker。</div>
          <p class="mt-1 text-xs text-slate-400">{{ store.meta.writable ? '已启动的 Agent 继续使用旧配置。' : '当前配置源只读，暂时无法保存。' }}</p>
        </div>
        <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
          {{ store.isSaving ? '保存中...' : '保存 MCP 配置' }}
        </AppButton>
      </div>
    </div>
  </section>
</template>
