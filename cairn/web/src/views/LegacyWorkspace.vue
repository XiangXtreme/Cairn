<script setup lang="ts">
const legacyUrl = '/static/legacy-index.html#/';
</script>

<template>
  <iframe
    :src="legacyUrl"
    title="Cairn workspace"
    class="block h-screen w-screen border-0 bg-white"
  />
</template>
