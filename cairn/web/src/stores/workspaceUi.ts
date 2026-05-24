import { computed, ref, watch } from 'vue';
import { defineStore } from 'pinia';

import type { LayoutMode, SideTab, WorkspacePrefs } from '@/types/workspace';
import { DEFAULT_PREFS, isValidLayoutMode, loadWorkspacePrefs, persistWorkspacePrefs } from '@/utils/workspace';

export type WorkspaceModal =
  | 'create'
  | 'hint'
  | 'complete'
  | 'rename'
  | 'clone'
  | 'reopen'
  | 'delete'
  | 'yaml'
  | 'intent'
  | 'conclude'
  | null;

export const useWorkspaceUiStore = defineStore('workspace-ui', () => {
  const prefs = ref<WorkspacePrefs>(loadWorkspacePrefs());
  const sideTab = ref<SideTab>('detail');
  const activeModal = ref<WorkspaceModal>(null);
  const exportTab = ref<'yaml' | 'timeline'>('yaml');
  const yamlPreviewTitle = ref('');
  const yamlPreviewText = ref('');
  const projectListScrollTop = ref(0);
  const pendingIntentId = ref('');
  const pendingDeleteProjectId = ref('');
  const pendingDeleteProjectTitle = ref('');

  const sidePanelWidth = computed({
    get: () => prefs.value.sidePanelWidth,
    set: (value: number) => {
      prefs.value.sidePanelWidth = Math.min(720, Math.max(280, Math.round(value)));
    },
  });
  const actorName = computed({
    get: () => prefs.value.actorName,
    set: (value: string) => {
      prefs.value.actorName = value.trim() || DEFAULT_PREFS.actorName;
    },
  });
  const layoutMode = computed({
    get: () => prefs.value.layoutMode,
    set: (value: LayoutMode) => {
      prefs.value.layoutMode = isValidLayoutMode(value) ? value : DEFAULT_PREFS.layoutMode;
    },
  });

  watch(
    prefs,
    (value) => {
      persistWorkspacePrefs(value);
    },
    { deep: true },
  );

  function openModal(modal: WorkspaceModal) {
    activeModal.value = modal;
  }

  function closeModal() {
    activeModal.value = null;
    pendingIntentId.value = '';
    pendingDeleteProjectId.value = '';
    pendingDeleteProjectTitle.value = '';
  }

  return {
    prefs,
    sideTab,
    activeModal,
    exportTab,
    yamlPreviewTitle,
    yamlPreviewText,
    projectListScrollTop,
    pendingIntentId,
    pendingDeleteProjectId,
    pendingDeleteProjectTitle,
    sidePanelWidth,
    actorName,
    layoutMode,
    openModal,
    closeModal,
  };
});
