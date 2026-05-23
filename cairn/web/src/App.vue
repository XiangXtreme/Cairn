<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';

import ToastHost from '@/components/ui/ToastHost.vue';
import LegacyWorkspace from '@/views/LegacyWorkspace.vue';
import SettingsView from '@/views/SettingsView.vue';

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
  return 'legacy';
});
</script>

<template>
  <SettingsView v-if="route === 'settings'" />
  <LegacyWorkspace v-else />
  <ToastHost />
</template>
