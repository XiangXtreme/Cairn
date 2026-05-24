import { computed, ref } from 'vue';
import { defineStore } from 'pinia';

import { api } from '@/api/client';
import { useUiStore } from '@/stores/ui';
import { useWorkspaceUiStore } from '@/stores/workspaceUi';
import type {
  CreateProjectRequest,
  ProjectDetail,
  ReplayState,
  TimelineEntry,
} from '@/types/workspace';
import {
  buildReplayFrames,
  buildTimeline,
  cloneProjectDetail,
  createEmptyReplayState,
  replayEventDurationMs,
} from '@/utils/workspace';

export const useProjectStore = defineStore('project', () => {
  const ui = useUiStore();
  const workspaceUi = useWorkspaceUiStore();
  const project = ref<ProjectDetail | null>(null);
  const isLoading = ref(false);
  const selectedNode = ref<{ type: 'fact' | 'intent'; id: string } | null>(null);
  const selectedFacts = ref<string[]>([]);
  const selectedTimelineEntryId = ref<string | null>(null);
  const replay = ref<ReplayState>(createEmptyReplayState());
  let replayTimer: number | null = null;

  const timeline = computed<TimelineEntry[]>(() =>
    replay.value.active ? replay.value.visibleEvents : buildTimeline(project.value),
  );
  const selectedFact = computed(() => {
    if (selectedNode.value?.type !== 'fact') return null;
    return project.value?.facts.find((fact) => fact.id === selectedNode.value?.id) || null;
  });
  const selectedIntent = computed(() => {
    if (selectedNode.value?.type !== 'intent') return null;
    return project.value?.intents.find((intent) => intent.id === selectedNode.value?.id) || null;
  });

  async function loadProject(projectId: string) {
    if (replay.value.active) {
      stopReplayTimer();
      replay.value = createEmptyReplayState(replay.value.stepMs);
    }
    isLoading.value = true;
    try {
      project.value = await api.getProject(projectId);
    } catch (error) {
      ui.showToast(error instanceof Error ? error.message : '加载项目失败', 'error');
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  function clearProject() {
    stopReplayTimer();
    replay.value = createEmptyReplayState(replay.value.stepMs);
    project.value = null;
    selectedNode.value = null;
    selectedFacts.value = [];
    selectedTimelineEntryId.value = null;
  }

  function selectFact(factId: string, exclusive = true) {
    selectedNode.value = { type: 'fact', id: factId };
    if (exclusive) selectedFacts.value = [factId];
    else if (!selectedFacts.value.includes(factId)) selectedFacts.value = [...selectedFacts.value, factId];
  }

  function selectIntent(intentId: string) {
    selectedNode.value = { type: 'intent', id: intentId };
    selectedTimelineEntryId.value = timeline.value.find((entry) => entry.intentId === intentId)?.id || null;
  }

  function clearSelection() {
    selectedNode.value = null;
    selectedFacts.value = [];
    selectedTimelineEntryId.value = null;
  }

  function openTimelineEntry(entry: TimelineEntry) {
    selectedTimelineEntryId.value = entry.id;
    if (entry.targetType === 'fact') selectFact(entry.targetId);
    if (entry.targetType === 'intent') selectIntent(entry.targetId);
  }

  function stopReplayTimer() {
    if (replayTimer) window.clearTimeout(replayTimer);
    replayTimer = null;
  }

  function applyReplayFrame(frameIndex: number) {
    if (!replay.value.active) return;
    const frame = replay.value.frames[frameIndex];
    if (!frame) return;
    replay.value.frameIndex = frameIndex;
    project.value = cloneProjectDetail(frame.project);
    replay.value.visibleEvents = replay.value.frames
      .slice(0, frameIndex + 1)
      .map((item) => JSON.parse(JSON.stringify(item.event)) as TimelineEntry)
      .filter((entry) => entry.type !== 'reason_started')
      .map((entry, index, list) => ({ ...entry, isLast: index === list.length - 1 }));
  }

  function scheduleReplayTick() {
    if (!replay.value.active || !replay.value.playing) return;
    if (replay.value.frameIndex >= replay.value.frames.length - 1) {
      replay.value.playing = false;
      return;
    }
    stopReplayTimer();
    const currentFrame = replay.value.frames[replay.value.frameIndex];
    const delay = replayEventDurationMs(currentFrame?.event, replay.value.stepMs);
    replayTimer = window.setTimeout(() => {
      advanceReplay();
    }, delay);
  }

  async function startReplay() {
    if (!project.value || replay.value.active) return;
    const sourceProject = await api.getProject(project.value.project.id);
    const baseEvents = buildTimeline(sourceProject).map((event) => ({
      ...JSON.parse(JSON.stringify(event)),
      meta: [...event.meta],
      sourceFactIds: [...event.sourceFactIds],
    })) as TimelineEntry[];
    const frames = buildReplayFrames(sourceProject, baseEvents);
    if (frames.length === 0) {
      throw new Error('没有可回放的时间线');
    }
    stopReplayTimer();
    replay.value = {
      active: true,
      playing: true,
      frameIndex: -1,
      frames,
      visibleEvents: [],
      sourceProject,
      stepMs: replay.value.stepMs || 1100,
    };
    selectedNode.value = null;
    selectedFacts.value = [];
    selectedTimelineEntryId.value = null;
    applyReplayFrame(0);
    scheduleReplayTick();
  }

  function advanceReplay() {
    if (!replay.value.active) return;
    if (replay.value.frameIndex >= replay.value.frames.length - 1) {
      replay.value.playing = false;
      stopReplayTimer();
      return;
    }
    applyReplayFrame(replay.value.frameIndex + 1);
    scheduleReplayTick();
  }

  function toggleReplay() {
    if (!replay.value.active) return;
    if (replay.value.playing) {
      replay.value.playing = false;
      stopReplayTimer();
      return;
    }
    if (replay.value.frameIndex >= replay.value.frames.length - 1) {
      restartReplay();
      return;
    }
    replay.value.playing = true;
    scheduleReplayTick();
  }

  function restartReplay() {
    if (!replay.value.active || replay.value.frames.length === 0) return;
    stopReplayTimer();
    replay.value.playing = true;
    selectedNode.value = null;
    selectedFacts.value = [];
    selectedTimelineEntryId.value = null;
    applyReplayFrame(0);
    scheduleReplayTick();
  }

  async function exitReplay() {
    if (!replay.value.active) return;
    const projectId = project.value?.project.id;
    const stepMs = replay.value.stepMs;
    stopReplayTimer();
    replay.value = createEmptyReplayState(stepMs);
    if (!projectId) return;
    project.value = await api.getProject(projectId);
  }

  async function createProject(body: CreateProjectRequest) {
    const created = await api.createProject(body);
    project.value = created;
    return created;
  }

  async function renameProject(title: string) {
    if (!project.value) return null;
    const meta = await api.updateProjectTitle(project.value.project.id, { title });
    project.value.project = meta;
    return meta;
  }

  async function cloneProject(title: string) {
    if (!project.value) return null;
    const cloned = await api.cloneProject(project.value.project.id, { title });
    return cloned;
  }

  async function deleteProject() {
    if (!project.value) return;
    await api.deleteProject(project.value.project.id);
    clearProject();
  }

  async function updateProjectStatus(status: 'active' | 'stopped') {
    if (!project.value) return null;
    const meta = await api.updateProjectStatus(project.value.project.id, { status });
    project.value.project = meta;
    return meta;
  }

  async function createHint(content: string) {
    if (!project.value) return null;
    const hint = await api.createHint(project.value.project.id, {
      content,
      creator: workspaceUi.actorName,
    });
    project.value.hints.push(hint);
    return hint;
  }

  async function createIntent(description: string, from: string[]) {
    if (!project.value) return null;
    const intent = await api.createIntent(project.value.project.id, {
      description,
      from,
      creator: workspaceUi.actorName,
    });
    project.value.intents.push(intent);
    return intent;
  }

  async function heartbeatIntent(intentId: string) {
    if (!project.value) return null;
    const intent = await api.heartbeatIntent(project.value.project.id, intentId, {
      worker: workspaceUi.actorName,
    });
    replaceIntent(intent);
    return intent;
  }

  async function releaseIntent(intentId: string) {
    if (!project.value) return null;
    const intent = await api.releaseIntent(project.value.project.id, intentId, {
      worker: workspaceUi.actorName,
    });
    replaceIntent(intent);
    return intent;
  }

  async function concludeIntent(intentId: string, description: string) {
    if (!project.value) return null;
    const response = await api.concludeIntent(project.value.project.id, intentId, {
      worker: workspaceUi.actorName,
      description,
    });
    project.value.facts.push(response.fact);
    replaceIntent(response.intent);
    selectFact(response.fact.id);
    return response;
  }

  async function completeProject(description: string, from: string[]) {
    if (!project.value) return null;
    const intent = await api.completeProject(project.value.project.id, {
      description,
      from,
      worker: workspaceUi.actorName,
    });
    project.value.project.status = 'completed';
    project.value.project.reason = null;
    project.value.intents.push(intent);
    selectedNode.value = { type: 'fact', id: 'goal' };
    selectedFacts.value = ['goal'];
    return intent;
  }

  async function reopenProject(description: string) {
    if (!project.value) return null;
    const response = await api.reopenProject(project.value.project.id, {
      description,
      creator: workspaceUi.actorName,
    });
    project.value.project = response.project;
    project.value.facts.push(response.fact);
    project.value.intents.push(response.intent);
    selectFact(response.fact.id);
    return response;
  }

  async function loadExport(format: 'yaml' | 'timeline') {
    if (!project.value) return '';
    const text = await api.exportProject(project.value.project.id, format);
    workspaceUi.exportTab = format;
    workspaceUi.yamlPreviewText = text;
    workspaceUi.yamlPreviewTitle = `${project.value.project.id} - ${project.value.project.title}`;
    return text;
  }

  function replaceIntent(nextIntent: ProjectDetail['intents'][number]) {
    if (!project.value) return;
    project.value.intents = project.value.intents.map((intent) => (intent.id === nextIntent.id ? nextIntent : intent));
  }

  return {
    project,
    isLoading,
    selectedNode,
    selectedFacts,
    selectedTimelineEntryId,
    timeline,
    selectedFact,
    selectedIntent,
    replay,
    loadProject,
    clearProject,
    selectFact,
    selectIntent,
    clearSelection,
    openTimelineEntry,
    createProject,
    renameProject,
    cloneProject,
    deleteProject,
    updateProjectStatus,
    createHint,
    createIntent,
    heartbeatIntent,
    releaseIntent,
    concludeIntent,
    completeProject,
    reopenProject,
    loadExport,
    startReplay,
    advanceReplay,
    toggleReplay,
    restartReplay,
    exitReplay,
  };
});
