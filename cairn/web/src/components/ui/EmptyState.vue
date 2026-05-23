<script setup lang="ts">
defineProps<{
  title: string;
  detail?: string;
}>();
</script>

<template>
  <div class="rounded-3xl border border-dashed border-slate-200 bg-slate-50 px-5 py-10 text-center text-slate-400">
    <p class="text-sm">{{ title }}</p>
    <p v-if="detail" class="mt-1 text-xs">{{ detail }}</p>
  </div>
</template>
