<script setup lang="ts">
import EmptyState from '@/components/ui/EmptyState.vue';
import type { ProjectSummary } from '@/types/workspace';
import ProjectCard from './ProjectCard.vue';

defineProps<{
  projects: ProjectSummary[];
  selectedProjectId?: string;
}>();

const emit = defineEmits<{
  open: [projectId: string];
  preview: [projectId: string];
  toggle: [projectId: string, nextStatus: 'active' | 'stopped'];
  delete: [projectId: string];
}>();
</script>

<template>
  <section class="rounded-[28px] border border-slate-200 bg-white p-4 shadow-sm">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">项目列表</div>
        <h2 class="mt-1 text-lg font-semibold text-slate-900">Workspace</h2>
      </div>
      <div class="text-xs text-slate-400">点击项目卡进入详情视图</div>
    </div>

    <EmptyState
      v-if="projects.length === 0"
      title="还没有项目"
      detail="先创建一个项目，新的 Vue workspace 会直接接管列表、详情、图谱和时间线。"
    />

    <div v-else class="grid grid-cols-1 gap-4 xl:grid-cols-2 2xl:grid-cols-3">
      <ProjectCard
        v-for="project in projects"
        :key="project.id"
        :project="project"
        :selected="project.id === selectedProjectId"
        @open="emit('open', $event)"
        @preview="emit('preview', $event)"
        @toggle="(projectId, nextStatus) => emit('toggle', projectId, nextStatus)"
        @delete="emit('delete', $event)"
      />
    </div>
  </section>
</template>
