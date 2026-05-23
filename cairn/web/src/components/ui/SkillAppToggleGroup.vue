<script setup lang="ts">
type SkillAppKey = 'claude' | 'codex';

interface SkillAppItem {
  key: SkillAppKey;
  label: string;
  iconSrc: string;
  activeClass: string;
}

const props = withDefaults(
  defineProps<{
    enabledClaude: boolean;
    enabledCodex: boolean;
    disabled?: boolean;
  }>(),
  {
    disabled: false,
  },
);

const emit = defineEmits<{
  toggle: [app: SkillAppKey, enabled: boolean];
}>();

const claudeIcon = new URL('../../../../src/cairn/server/static/vendor/ccswitch-icons/claude.svg', import.meta.url).href;
const codexIcon = new URL('../../../../src/cairn/server/static/vendor/ccswitch-icons/chatgpt.svg', import.meta.url).href;

const items: SkillAppItem[] = [
  {
    key: 'claude',
    label: 'Claude Code',
    iconSrc: claudeIcon,
    activeClass: 'border-orange-200 bg-orange-50 text-orange-700 ring-1 ring-orange-200 shadow-sm shadow-orange-100',
  },
  {
    key: 'codex',
    label: 'Codex',
    iconSrc: codexIcon,
    activeClass: 'border-emerald-200 bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 shadow-sm shadow-emerald-100',
  },
];

function isEnabled(app: SkillAppKey) {
  return app === 'claude' ? props.enabledClaude : props.enabledCodex;
}

function toggle(app: SkillAppKey) {
  if (props.disabled) return;
  emit('toggle', app, !isEnabled(app));
}
</script>

<template>
  <div class="flex items-center gap-1.5">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :title="`${item.label}${isEnabled(item.key) ? ' 已启用' : ' 未启用'}`"
      :aria-label="`${item.label}${isEnabled(item.key) ? ' 已启用' : ' 未启用'}`"
      :aria-pressed="isEnabled(item.key)"
      :disabled="disabled"
      class="flex h-8 w-8 items-center justify-center rounded-xl border transition-all duration-150 disabled:cursor-not-allowed disabled:opacity-30"
      :class="[
        isEnabled(item.key)
          ? item.activeClass
          : 'border-transparent bg-slate-100 text-slate-400 opacity-40 hover:border-slate-200 hover:bg-white hover:opacity-85',
      ]"
      @click="toggle(item.key)"
    >
      <img
        :src="item.iconSrc"
        :alt="item.label"
        class="h-4 w-4 object-contain"
        :class="isEnabled(item.key) ? '' : 'grayscale'"
      />
    </button>
  </div>
</template>
