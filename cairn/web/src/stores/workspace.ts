import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { api } from '@/api/client';
import { useUiStore } from '@/stores/ui';
import type { ProjectMeta, ProjectStatus, ProjectSummary } from '@/types/workspace';

export const useWorkspaceStore = defineStore('workspace', () => {
  const ui = useUiStore();
  const projects = ref<ProjectSummary[]>([]);
  const isLoading = ref(false);
  const selectedProjectId = ref('');
  const pollTimer = ref<number | null>(null);

  const activeCount = computed(() => projects.value.filter((project) => project.status === 'active').length);
  const stoppedCount = computed(() => projects.value.filter((project) => project.status === 'stopped').length);
  const completedCount = computed(() => projects.value.filter((project) => project.status === 'completed').length);

  async function loadProjects() {
    isLoading.value = true;
    try {
      projects.value = await api.listProjects();
    } catch (error) {
      ui.showToast(error instanceof Error ? error.message : '加载项目失败', 'error');
    } finally {
      isLoading.value = false;
    }
  }

  function setSelectedProject(projectId: string) {
    selectedProjectId.value = projectId;
  }

  function upsertProjectMeta(meta: ProjectMeta) {
    const index = projects.value.findIndex((project) => project.id === meta.id);
    if (index >= 0) {
      const current = projects.value[index];
      projects.value[index] = {
        ...current,
        ...meta,
      };
      return;
    }
    void loadProjects();
  }

  function removeProject(projectId: string) {
    projects.value = projects.value.filter((project) => project.id !== projectId);
    if (selectedProjectId.value === projectId) selectedProjectId.value = '';
  }

  async function updateProjectStatus(projectId: string, status: Extract<ProjectStatus, 'active' | 'stopped'>) {
    const updated = await api.updateProjectStatus(projectId, { status });
    upsertProjectMeta(updated);
    return updated;
  }

  async function pauseAllActiveProjects() {
    const candidates = projects.value.filter((project) => project.status === 'active');
    await Promise.all(candidates.map((project) => updateProjectStatus(project.id, 'stopped')));
  }

  function startPolling(callback: () => Promise<void>) {
    stopPolling();
    pollTimer.value = window.setInterval(() => {
      void callback();
    }, 5000);
  }

  function stopPolling() {
    if (pollTimer.value) window.clearInterval(pollTimer.value);
    pollTimer.value = null;
  }

  return {
    projects,
    isLoading,
    selectedProjectId,
    activeCount,
    stoppedCount,
    completedCount,
    loadProjects,
    setSelectedProject,
    upsertProjectMeta,
    removeProject,
    updateProjectStatus,
    pauseAllActiveProjects,
    startPolling,
    stopPolling,
  };
});
