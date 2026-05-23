import { defineStore } from 'pinia';
import { ref } from 'vue';

import type { ToastType } from '@/types/dispatch';

export type SettingsSection = 'mode' | 'providers' | 'workers' | 'mcp' | 'skills' | 'runtime';

export const useUiStore = defineStore('ui', () => {
  const settingsSection = ref<SettingsSection>('mode');
  const toast = ref<{ show: boolean; message: string; type: ToastType }>({
    show: false,
    message: '',
    type: 'info',
  });
  let toastTimer: number | undefined;

  function openSettingsSection(section: SettingsSection) {
    settingsSection.value = section;
  }

  function showToast(message: string, type: ToastType = 'info') {
    toast.value = { show: true, message, type };
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.value.show = false;
    }, 3200);
  }

  return {
    settingsSection,
    toast,
    openSettingsSection,
    showToast,
  };
});
