<script setup lang="ts">
import { FolderSearch, PackagePlus, Plus, Save, Trash2 } from 'lucide-vue-next';

import AppButton from '@/components/ui/AppButton.vue';
import BadgePill from '@/components/ui/BadgePill.vue';
import EmptyState from '@/components/ui/EmptyState.vue';
import FormField from '@/components/ui/FormField.vue';
import SkillAppToggleGroup from '@/components/ui/SkillAppToggleGroup.vue';
import TextInput from '@/components/ui/TextInput.vue';
import { useDispatchSettingsStore } from '@/stores/dispatchSettings';
import { useUiStore } from '@/stores/ui';
import type { SkillSettings } from '@/types/dispatch';

const store = useDispatchSettingsStore();
const ui = useUiStore();

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      resolve(result.includes(',') ? result.split(',')[1] : result);
    };
    reader.onerror = () => reject(reader.error || new Error('读取文件失败'));
    reader.readAsDataURL(file);
  });
}

async function onZipSelected(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  try {
    await store.importSkillZip(file.name, await fileToBase64(file));
  } catch (error) {
    ui.showToast(error instanceof Error ? error.message : String(error), 'error');
  } finally {
    input.value = '';
  }
}

function toggleSkillApp(skill: SkillSettings, app: 'claude' | 'codex', enabled: boolean) {
  if (app === 'claude') {
    skill.enabled_claude = enabled;
    return;
  }
  skill.enabled_codex = enabled;
}
</script>

<template>
  <section class="overflow-hidden rounded-3xl border border-slate-200/70 bg-white shadow-sm">
    <div class="border-b border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div class="min-w-0">
          <div class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">Skill</div>
          <h3 class="mt-1 text-2xl font-semibold tracking-tight text-slate-900">本地 Skill 注册</h3>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            管理可注入到 Claude Code / Codex Worker 的本地 Skill，并在 Worker 面板里按需绑定。
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <AppButton :icon="FolderSearch" @click="store.discoverSkills()">扫描 Skill</AppButton>
          <label class="inline-flex cursor-pointer items-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50">
            <PackagePlus class="h-4 w-4" aria-hidden="true" />
            导入 zip
            <input type="file" accept=".zip" class="hidden" @change="onZipSelected" />
          </label>
          <AppButton variant="primary" :icon="Plus" @click="store.addSkill()">新增 Skill</AppButton>
        </div>
      </div>
    </div>

    <div v-if="store.discoveredSkills.length" class="border-b border-slate-200/80 bg-slate-50/60 px-5 py-5 lg:px-8">
      <div class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">扫描结果</div>
      <div class="mt-3 grid grid-cols-1 gap-3 xl:grid-cols-2">
        <div
          v-for="skill in store.discoveredSkills"
          :key="skill.id"
          class="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 md:flex-row md:items-start md:justify-between"
        >
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <span class="font-medium text-slate-900">{{ skill.name || skill.id }}</span>
              <BadgePill :tone="skill.already_registered ? 'teal' : 'brand'">
                {{ skill.already_registered ? '已注册' : '可注册' }}
              </BadgePill>
            </div>
            <p v-if="skill.description" class="mt-1 text-xs leading-5 text-slate-500">{{ skill.description }}</p>
            <p class="mt-1 break-all text-[11px] text-slate-400">{{ skill.path }}</p>
          </div>
          <AppButton size="sm" :disabled="skill.already_registered" @click="store.registerDiscoveredSkill(skill)">注册</AppButton>
        </div>
      </div>
    </div>

    <div class="space-y-4 px-5 py-5 lg:px-8">
      <article
        v-for="(skill, idx) in store.form.skills"
        :key="idx"
        class="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm"
      >
        <div class="flex flex-col gap-4 border-b border-slate-200/80 bg-slate-50/80 px-4 py-4 lg:px-6 xl:flex-row xl:items-start xl:justify-between">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <BadgePill :tone="skill.enabled ? 'teal' : 'slate'">{{ skill.enabled ? '启用中' : '已禁用' }}</BadgePill>
              <span class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-400">客户端</span>
              <SkillAppToggleGroup
                :enabled-claude="skill.enabled_claude"
                :enabled-codex="skill.enabled_codex"
                @toggle="(app, enabled) => toggleSkillApp(skill, app, enabled)"
              />
            </div>
            <div class="mt-3 truncate text-base font-semibold text-slate-900">{{ skill.name || skill.id || '未命名 Skill' }}</div>
            <div class="mt-1 break-all text-xs text-slate-500">{{ skill.path || '未设置路径' }}</div>
            <div class="mt-2 text-xs leading-5 text-slate-400">点亮上方图标后，这个 Skill 才会出现在对应客户端 Worker 的可绑定列表里。</div>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <AppButton size="sm" :variant="skill.enabled ? 'secondary' : 'brand'" @click="skill.enabled = !skill.enabled">
              {{ skill.enabled ? '禁用' : '启用' }}
            </AppButton>
            <AppButton size="sm" variant="danger" :icon="Trash2" @click="store.removeSkill(idx)">移除</AppButton>
          </div>
        </div>

        <div class="grid grid-cols-1 gap-4 px-4 py-5 lg:px-6 md:grid-cols-2">
          <FormField label="标识">
            <TextInput v-model="skill.id" />
          </FormField>
          <FormField label="名称">
            <TextInput v-model="skill.name" />
          </FormField>
          <FormField label="路径" class="md:col-span-2">
            <TextInput v-model="skill.path" />
          </FormField>
          <FormField label="描述" class="md:col-span-2">
            <textarea
              v-model="skill.description"
              rows="3"
              class="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-3 py-2.5 text-sm leading-6 text-slate-700 transition focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
            />
          </FormField>
        </div>
      </article>

      <EmptyState
        v-if="store.form.skills.length === 0"
        title="还没有注册 Skill"
        detail="扫描或导入 Skill 后，可以在 Worker 面板里启用。"
      />
    </div>

    <div class="border-t border-slate-200/80 px-5 py-5 lg:px-8">
      <div class="flex flex-col justify-between gap-4 rounded-[24px] border border-slate-200 bg-slate-50/80 px-5 py-4 lg:flex-row lg:items-center">
        <div>
          <div class="text-sm font-medium text-slate-800">保存后会同步到后续启动的 Claude / Codex Worker。</div>
          <p class="mt-1 text-xs text-slate-400">{{ store.meta.writable ? 'Worker 绑定会随配置一起保存。' : '当前配置源只读，暂时无法保存。' }}</p>
        </div>
        <AppButton variant="primary" :icon="Save" :disabled="store.isSaving || !!store.loadError || !store.meta.writable" @click="store.saveDispatchSettings()">
          {{ store.isSaving ? '保存中...' : '保存 Skill 配置' }}
        </AppButton>
      </div>
    </div>
  </section>
</template>
