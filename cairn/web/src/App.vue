<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import ToastHost from '@/components/ui/ToastHost.vue';
import SettingsView from '@/views/SettingsView.vue';
import WorkspaceView from '@/views/WorkspaceView.vue';

const hash = ref(window.location.hash || '#/');

function updateHash() {
  hash.value = window.location.hash || '#/';
}

onMounted(() => {
  window.addEventListener('hashchange', updateHash);
});

onUnmounted(() => {
  window.removeEventListener('hashchange', updateHash);
});

const route = computed(() => {
  if (hash.value === '#/settings') return 'settings';
  return 'workspace';
});
</script>

<template>
  <SettingsView v-if="route === 'settings'" />
  <WorkspaceView v-else />
  <ToastHost />
</template>
