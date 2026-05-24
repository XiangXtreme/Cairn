<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';

import ModalShell from '@/components/ui/ModalShell.vue';
import AppButton from '@/components/ui/AppButton.vue';
import FormField from '@/components/ui/FormField.vue';
import TextInput from '@/components/ui/TextInput.vue';
import GraphCanvas from '@/components/workspace/GraphCanvas.vue';
import ProjectActionBar from '@/components/workspace/ProjectActionBar.vue';
import ProjectReplayBar from '@/components/workspace/ProjectReplayBar.vue';
import ProjectSection from '@/components/workspace/ProjectSection.vue';
import ProjectSidebar from '@/components/workspace/ProjectSidebar.vue';
import WorkspaceHeader from '@/components/workspace/WorkspaceHeader.vue';
import WorkspaceOverview from '@/components/workspace/WorkspaceOverview.vue';
import { api } from '@/api/client';
import { useProjectStore } from '@/stores/project';
import { useUiStore } from '@/stores/ui';
import { useWorkspaceStore } from '@/stores/workspace';
import { useWorkspaceUiStore } from '@/stores/workspaceUi';
import { getProjectRunningState } from '@/utils/workspace';

const ui = useUiStore();
const workspace = useWorkspaceStore();
const projectStore = useProjectStore();
const workspaceUi = useWorkspaceUiStore();

const workspaceRefs = storeToRefs(workspace);
const projectRefs = storeToRefs(projectStore);
const workspaceUiRefs = storeToRefs(workspaceUi);
const routeHash = ref(window.location.hash || '#/');

const forms = reactive({
  create: { title: '', origin: '', goal: '', hint: '' },
  rename: { title: '' },
  clone: { title: '' },
  hint: { content: '' },
  complete: { description: '' },
  reopen: { description: '' },
  intent: { description: '' },
  conclude: { description: '' },
});
const deleteState = reactive({
  submitting: false,
});

const currentRouteProjectId = computed(() => {
  const match = routeHash.value.match(/^#\/projects\/(.+)$/);
  return match ? decodeURIComponent(match[1]) : '';
});
const isProjectDetailRoute = computed(() => Boolean(currentRouteProjectId.value));

const selectedProjectTitle = computed(() => projectRefs.project.value?.project.title || '');
const selectedFactId = computed(() => (projectRefs.selectedNode.value?.type === 'fact' ? projectRefs.selectedNode.value.id : null));
const selectedIntentId = computed(() => (projectRefs.selectedNode.value?.type === 'intent' ? projectRefs.selectedNode.value.id : null));
const activeReason = computed(() => getProjectRunningState(projectRefs.project.value));

function goSettings() {
  window.location.hash = '#/settings';
}

function goHome() {
  window.location.hash = '#/';
}

async function syncRoute() {
  const projectId = currentRouteProjectId.value;
  if (!projectId) {
    workspace.setSelectedProject('');
    projectStore.clearProject();
    return;
  }
  if (workspace.selectedProjectId !== projectId || projectRefs.project.value?.project.id !== projectId) {
    workspace.setSelectedProject(projectId);
    await projectStore.loadProject(projectId);
  }
}

async function refresh() {
  await workspace.loadProjects();
  if (workspace.selectedProjectId && !projectRefs.replay.value.active) {
    await projectStore.loadProject(workspace.selectedProjectId);
  }
}

async function openProject(projectId: string) {
  workspace.setSelectedProject(projectId);
  if (projectRefs.project.value?.project.id !== projectId) {
    await projectStore.loadProject(projectId);
  }
  window.location.hash = `#/projects/${encodeURIComponent(projectId)}`;
}

function openCreateModal() {
  workspaceUi.openModal('create');
}

async function openPreview(projectId: string) {
  await openProject(projectId);
  await projectStore.loadExport('yaml');
  workspaceUi.openModal('yaml');
}

async function toggleProjectStatus(projectId: string, nextStatus: 'active' | 'stopped') {
  await workspace.updateProjectStatus(projectId, nextStatus);
  if (projectRefs.project.value?.project.id === projectId) {
    await projectStore.updateProjectStatus(nextStatus);
  }
}

function askDelete(projectId?: string) {
  const targetId = projectId || projectRefs.project.value?.project.id || workspace.selectedProjectId;
  const targetProject =
    workspaceRefs.projects.value.find((item) => item.id === targetId)
    || (projectRefs.project.value?.project.id === targetId ? projectRefs.project.value.project : null);
  workspaceUi.pendingDeleteProjectId = targetId || '';
  workspaceUi.pendingDeleteProjectTitle = targetProject?.title || targetId || '';
  workspaceUi.openModal('delete');
}

function seedRename() {
  forms.rename.title = projectRefs.project.value?.project.title || '';
  workspaceUi.openModal('rename');
}

function seedClone() {
  forms.clone.title = `${projectRefs.project.value?.project.title || ''}（克隆）`;
  workspaceUi.openModal('clone');
}

async function seedCloneFromProject(projectId: string) {
  const projectMeta = workspaceRefs.projects.value.find((item) => item.id === projectId);
  workspace.setSelectedProject(projectId);
  forms.clone.title = `${projectMeta?.title || projectId}（克隆）`;
  if (projectRefs.project.value?.project.id !== projectId) {
    await projectStore.loadProject(projectId);
  }
  workspaceUi.openModal('clone');
}

function seedConclude(intentId?: string) {
  if (intentId) {
    workspaceUi.pendingIntentId = intentId;
    projectStore.selectIntent(intentId);
  } else if (selectedIntentId.value) {
    workspaceUi.pendingIntentId = selectedIntentId.value;
  }
  forms.conclude.description = '';
  workspaceUi.openModal('conclude');
}

function resetForms() {
  forms.create = { title: '', origin: '', goal: '', hint: '' };
  forms.rename.title = '';
  forms.clone.title = '';
  forms.hint.content = '';
  forms.complete.description = '';
  forms.reopen.description = '';
  forms.intent.description = '';
  forms.conclude.description = '';
}

async function submitCreate() {
  const created = await projectStore.createProject({
    title: forms.create.title,
    origin: forms.create.origin,
    goal: forms.create.goal,
    hints: forms.create.hint.trim() ? [{ content: forms.create.hint.trim(), creator: workspaceUi.actorName }] : [],
  });
  await workspace.loadProjects();
  workspaceUi.closeModal();
  resetForms();
  await openProject(created.project.id);
}

async function submitRename() {
  await projectStore.renameProject(forms.rename.title);
  await workspace.loadProjects();
  workspaceUi.closeModal();
}

async function submitClone() {
  const cloned = await projectStore.cloneProject(forms.clone.title, workspace.selectedProjectId || undefined);
  await workspace.loadProjects();
  workspaceUi.closeModal();
  if (cloned) await openProject(cloned.project.id);
}

async function submitHint() {
  await projectStore.createHint(forms.hint.content);
  workspaceUi.closeModal();
}

async function submitIntent() {
  await projectStore.createIntent(forms.intent.description, projectRefs.selectedFacts.value);
  workspaceUi.closeModal();
}

async function submitComplete() {
  await projectStore.completeProject(forms.complete.description, projectRefs.selectedFacts.value);
  await workspace.loadProjects();
  workspaceUi.closeModal();
}

async function submitReopen() {
  await projectStore.reopenProject(forms.reopen.description);
  await workspace.loadProjects();
  workspaceUi.closeModal();
}

async function submitConclude() {
  if (!workspaceUi.pendingIntentId) return;
  await projectStore.concludeIntent(workspaceUi.pendingIntentId, forms.conclude.description);
  workspaceUi.closeModal();
}

async function claimIntent(intentId: string) {
  await projectStore.heartbeatIntent(intentId);
}

async function releaseIntent(intentId: string) {
  await projectStore.releaseIntent(intentId);
}

async function startReplay() {
  await projectStore.startReplay();
  workspaceUi.sideTab = 'timeline';
}

function toggleReplay() {
  projectStore.toggleReplay();
}

function advanceReplay() {
  projectStore.advanceReplay();
}

function restartReplay() {
  projectStore.restartReplay();
}

async function exitReplay() {
  await projectStore.exitReplay();
}

async function submitDelete() {
  if (!workspaceUi.pendingDeleteProjectId || deleteState.submitting) return;
  deleteState.submitting = true;
  const deletingId = workspaceUi.pendingDeleteProjectId;
  const deletingTitle = workspaceUi.pendingDeleteProjectTitle || deletingId;
  const deletingCurrentDetail = projectRefs.project.value?.project.id === deletingId;
  const finishDelete = async (toastMessage?: string) => {
    workspace.removeProject(deletingId);
    workspaceUi.closeModal();
    if (deletingCurrentDetail || currentRouteProjectId.value === deletingId) {
      projectStore.clearProject();
      goHome();
    }
    await workspace.loadProjects();
    if (toastMessage) {
      ui.showToast(toastMessage, 'success');
    }
  };
  try {
    if (deletingCurrentDetail) {
      await projectStore.deleteProject();
    } else {
      await api.deleteProject(deletingId);
    }
    await finishDelete(`已删除项目 ${deletingTitle}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : `删除项目 ${deletingTitle} 失败`;
    if (message === 'Project not found' || message === 'HTTP 404') {
      await workspace.loadProjects();
      const stillExists = workspace.projects.some((item) => item.id === deletingId);
      if (!stillExists) {
        await finishDelete(`已删除项目 ${deletingTitle}`);
        return;
      }
    }
    ui.showToast(message, 'error');
  } finally {
    deleteState.submitting = false;
  }
}

async function openYaml() {
  await projectStore.loadExport(workspaceUi.exportTab);
  workspaceUi.openModal('yaml');
}

async function switchExport(tab: 'yaml' | 'timeline') {
  workspaceUi.exportTab = tab;
  await projectStore.loadExport(tab);
}

function updateActorName(value: string | number | null) {
  workspaceUi.actorName = value == null ? '' : String(value);
}

function closeModal() {
  workspaceUi.closeModal();
}

function onHashChange() {
  routeHash.value = window.location.hash || '#/';
  void syncRoute();
}

onMounted(async () => {
  window.addEventListener('hashchange', onHashChange);
  routeHash.value = window.location.hash || '#/';
  await workspace.loadProjects();
  await syncRoute();
  workspace.startPolling(refresh);
});

onUnmounted(() => {
  workspace.stopPolling();
  window.removeEventListener('hashchange', onHashChange);
});
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <WorkspaceHeader
      :project-count="workspaceRefs.projects.value.length"
      :selected-project-title="selectedProjectTitle"
      @create="openCreateModal"
      @settings="goSettings"
      @pause-all="workspace.pauseAllActiveProjects()"
    />

    <main class="space-y-5 px-4 py-5 lg:px-6 xl:px-8">
      <template v-if="!isProjectDetailRoute">
        <WorkspaceOverview
          :active-count="workspaceRefs.activeCount.value"
          :stopped-count="workspaceRefs.stoppedCount.value"
          :completed-count="workspaceRefs.completedCount.value"
          :selected-project-id="workspaceRefs.selectedProjectId.value"
        />

        <ProjectSection
          :projects="workspaceRefs.projects.value"
          :selected-project-id="workspaceRefs.selectedProjectId.value"
          @open="openProject"
          @preview="openPreview"
          @toggle="toggleProjectStatus"
          @clone="seedCloneFromProject"
          @delete="askDelete"
        />
      </template>

      <section v-else-if="projectRefs.project.value" class="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_320px] 2xl:grid-cols-[minmax(0,1fr)_340px]">
        <div class="min-w-0 space-y-5">
          <ProjectReplayBar
            :replay="projectRefs.replay.value"
            @toggle="toggleReplay"
            @restart="restartReplay"
            @advance="advanceReplay"
            @exit="exitReplay"
          />

          <ProjectActionBar
            :project="projectRefs.project.value"
            :replay-active="projectRefs.replay.value.active"
            @back="goHome"
            @toggle-status="projectRefs.project.value.project.status === 'active' ? toggleProjectStatus(projectRefs.project.value.project.id, 'stopped') : toggleProjectStatus(projectRefs.project.value.project.id, 'active')"
            @hint="workspaceUi.openModal('hint')"
            @complete="workspaceUi.openModal('complete')"
            @rename="seedRename"
            @clone="seedClone"
            @reopen="workspaceUi.openModal('reopen')"
            @delete="askDelete()"
            @yaml="openYaml"
            @intent="workspaceUi.openModal('intent')"
            @replay="startReplay"
          />

          <section class="relative">
            <div v-if="activeReason" class="absolute right-3 top-14 z-10 max-w-80">
              <div class="reason-panel-running relative overflow-hidden rounded-2xl border border-sky-200/80 bg-white/92 px-3.5 py-3 shadow-lg shadow-sky-100/60 backdrop-blur">
                <div class="flex items-start gap-3">
                  <span class="reason-beacon mt-1 shrink-0" />
                  <div class="min-w-0">
                    <div class="text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-500">推理运行中</div>
                    <div class="mt-0.5 truncate text-sm font-semibold text-slate-700">{{ activeReason.worker }}</div>
                    <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-500">
                      <span v-if="activeReason.trigger">触发 {{ activeReason.trigger }}</span>
                      <span>心跳 {{ new Date(activeReason.last_heartbeat_at).toLocaleString('zh-CN') }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="activeReason" class="reason-graph-scan z-[1]">
              <span class="reason-graph-grid" />
              <span class="reason-graph-ambient" />
              <span class="reason-graph-scanline" />
              <span class="reason-graph-sweep" />
            </div>

            <GraphCanvas
              :project="projectRefs.project.value"
              :layout-mode="workspaceUiRefs.layoutMode.value"
              :selected-node="projectRefs.selectedNode.value"
              :selected-facts="projectRefs.selectedFacts.value"
              @select-fact="projectStore.selectFact"
              @select-intent="projectStore.selectIntent"
              @clear="projectStore.clearSelection"
              @layout="workspaceUi.layoutMode = $event"
            />
          </section>
        </div>

        <ProjectSidebar
          :project="projectRefs.project.value"
          :side-tab="workspaceUiRefs.sideTab.value"
          :selected-fact-id="selectedFactId"
          :selected-intent-id="selectedIntentId"
          :selected-timeline-entry-id="projectRefs.selectedTimelineEntryId.value"
          :entries="projectRefs.timeline.value"
          :actor-name="workspaceUiRefs.actorName.value"
          :side-panel-width="workspaceUiRefs.sidePanelWidth.value"
          :replay-active="projectRefs.replay.value.active"
          @tab="workspaceUi.sideTab = $event"
          @timeline="projectStore.openTimelineEntry"
          @select-fact="projectStore.selectFact"
          @select-intent="projectStore.selectIntent"
          @update-actor-name="updateActorName"
          @claim-intent="claimIntent"
          @release-intent="releaseIntent"
          @conclude-intent="seedConclude"
        />
      </section>
    </main>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'create'" title="新建项目" description="填写起点与目标后，系统将直接进入项目详情页。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="项目标题"><TextInput v-model="forms.create.title" /></FormField>
        <FormField label="起点"><textarea v-model="forms.create.origin" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <FormField label="目标"><textarea v-model="forms.create.goal" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <FormField label="初始提示"><textarea v-model="forms.create.hint" class="min-h-24 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitCreate">创建并进入</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'rename'" title="重命名项目" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="标题"><TextInput v-model="forms.rename.title" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitRename">保存</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'clone'" title="克隆项目" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="新项目标题"><TextInput v-model="forms.clone.title" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitClone">克隆</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'hint'" title="添加提示" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="提示内容"><textarea v-model="forms.hint.content" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitHint">添加</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'intent'" title="创建意图" description="当前使用已选中的事实作为来源。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="意图描述"><textarea v-model="forms.intent.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="text-xs text-slate-400">来源：{{ projectRefs.selectedFacts.value.join(', ') || '未选择 facts' }}</div>
        <div class="flex justify-end"><AppButton variant="brand" :disabled="projectRefs.selectedFacts.value.length === 0" @click="submitIntent">创建意图</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'complete'" title="完成项目" description="使用当前选中的 facts 作为完成来源。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="完成说明"><textarea v-model="forms.complete.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="text-xs text-slate-400">来源：{{ projectRefs.selectedFacts.value.join(', ') || '未选择 facts' }}</div>
        <div class="flex justify-end"><AppButton variant="brand" :disabled="projectRefs.selectedFacts.value.length === 0" @click="submitComplete">标记完成</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'reopen'" title="重新打开项目" description="为已完成项目追加新的外部反馈事实。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="反馈描述"><textarea v-model="forms.reopen.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitReopen">重新打开</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'delete'" title="删除项目" description="这个动作会删除数据库记录和运行时产物。" @close="closeModal">
      <div class="space-y-4 p-5">
        <div class="rounded-2xl border border-rose-100 bg-rose-50/70 px-4 py-3">
          <div class="text-xs font-medium uppercase tracking-[0.14em] text-rose-500">即将删除</div>
          <div class="mt-1 text-sm font-semibold text-rose-900">
            {{ workspaceUiRefs.pendingDeleteProjectTitle.value || workspaceUiRefs.pendingDeleteProjectId.value || '当前项目' }}
          </div>
          <div class="mt-1 text-xs text-rose-700">
            {{ workspaceUiRefs.pendingDeleteProjectId.value }}
          </div>
        </div>
        <p class="text-sm text-slate-600">确认删除这个项目？删除后会立即从列表中移除，且无法恢复。</p>
        <div class="flex justify-end gap-2">
          <AppButton :disabled="deleteState.submitting" @click="closeModal">取消</AppButton>
          <AppButton variant="danger" :disabled="deleteState.submitting" @click="submitDelete">
            {{ deleteState.submitting ? '删除中...' : '确认删除' }}
          </AppButton>
        </div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'conclude'" title="提交结论" description="为当前已认领的意图生成新的事实。" @close="closeModal">
      <div class="space-y-4 p-5">
        <div class="text-xs text-slate-400">意图：{{ workspaceUiRefs.pendingIntentId.value || selectedIntentId }}</div>
        <FormField label="结论描述"><textarea v-model="forms.conclude.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitConclude">提交结论</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'yaml'" title="导出预览" :description="workspaceUiRefs.yamlPreviewTitle.value" wide @close="closeModal">
      <div class="space-y-4 p-5">
        <div class="flex items-center gap-2">
          <button
            type="button"
            class="rounded-2xl px-3 py-1.5 text-xs font-medium transition"
            :class="workspaceUiRefs.exportTab.value === 'yaml' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'"
            @click="switchExport('yaml')"
          >
            YAML
          </button>
          <button
            type="button"
            class="rounded-2xl px-3 py-1.5 text-xs font-medium transition"
            :class="workspaceUiRefs.exportTab.value === 'timeline' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600'"
            @click="switchExport('timeline')"
          >
            Timeline
          </button>
        </div>
        <pre class="max-h-[60vh] overflow-auto rounded-3xl border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">{{ workspaceUiRefs.yamlPreviewText.value }}</pre>
      </div>
    </ModalShell>
  </div>
</template>

<style scoped>
.reason-panel-running::before {
  content: "";
  position: absolute;
  inset: -6px;
  border-radius: 22px;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.14), rgba(56, 189, 248, 0));
  animation: reasonPanelPulse 2.1s ease-out infinite;
  pointer-events: none;
}

.reason-beacon {
  position: relative;
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  background: #0ea5e9;
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.16);
}

.reason-beacon::after {
  content: "";
  position: absolute;
  inset: -6px;
  border-radius: 9999px;
  border: 1.5px solid rgba(14, 165, 233, 0.34);
  animation: reasonBeaconPulse 1.8s ease-out infinite;
}

.reason-graph-scan {
  position: absolute;
  inset: 8px;
  overflow: hidden;
  pointer-events: none;
  border-radius: 18px;
}

.reason-graph-scan::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow:
    inset 0 0 0 1px rgba(125, 211, 252, 0.32),
    inset 0 0 30px rgba(125, 211, 252, 0.06),
    inset 0 0 64px rgba(56, 189, 248, 0.03);
  animation: reasonFramePulse 2.8s ease-in-out infinite;
}

.reason-graph-scan::after {
  content: "";
  position: absolute;
  inset: 12px;
  border-radius: 12px;
  background:
    linear-gradient(90deg, rgba(125, 211, 252, 0.85), rgba(125, 211, 252, 0.18)),
    linear-gradient(180deg, rgba(125, 211, 252, 0.85), rgba(125, 211, 252, 0.18)),
    linear-gradient(270deg, rgba(125, 211, 252, 0.85), rgba(125, 211, 252, 0.18)),
    linear-gradient(0deg, rgba(125, 211, 252, 0.85), rgba(125, 211, 252, 0.18));
  background-size: 18px 2px, 2px 18px, 18px 2px, 2px 18px;
  background-position: left top, left top, right bottom, right bottom;
  background-repeat: no-repeat;
  opacity: 0.6;
}

.reason-graph-scan > span {
  position: absolute;
  inset: 0;
  display: block;
}

.reason-graph-grid {
  inset: 12px;
  border-radius: 12px;
  background:
    repeating-linear-gradient(
      90deg,
      rgba(186, 230, 253, 0) 0,
      rgba(186, 230, 253, 0) 35px,
      rgba(186, 230, 253, 0.045) 36px,
      rgba(186, 230, 253, 0.045) 37px
    ),
    repeating-linear-gradient(
      180deg,
      rgba(186, 230, 253, 0) 0,
      rgba(186, 230, 253, 0) 35px,
      rgba(186, 230, 253, 0.04) 36px,
      rgba(186, 230, 253, 0.04) 37px
    );
  opacity: 0.42;
}

.reason-graph-ambient {
  inset: 0;
  background:
    radial-gradient(circle at 12% 18%, rgba(56, 189, 248, 0.11), rgba(56, 189, 248, 0) 30%),
    radial-gradient(circle at 84% 16%, rgba(59, 130, 246, 0.08), rgba(59, 130, 246, 0) 24%),
    linear-gradient(180deg, rgba(186, 230, 253, 0.055), rgba(255, 255, 255, 0) 46%);
  animation: reasonAmbientPulse 2.4s ease-in-out infinite alternate;
}

.reason-graph-scanline::before {
  content: "";
  position: absolute;
  left: 10px;
  right: 10px;
  height: 2px;
  top: 12%;
  background: linear-gradient(90deg, rgba(56, 189, 248, 0), rgba(186, 230, 253, 0.96), rgba(56, 189, 248, 0));
  box-shadow:
    0 0 18px rgba(125, 211, 252, 0.42),
    0 0 34px rgba(186, 230, 253, 0.16);
  animation: reasonGraphScanline 4.2s linear infinite;
}

.reason-graph-sweep {
  inset: -18%;
  background: linear-gradient(
    103deg,
    rgba(14, 165, 233, 0) 40%,
    rgba(56, 189, 248, 0.04) 47%,
    rgba(255, 255, 255, 0.22) 50%,
    rgba(125, 211, 252, 0.1) 53%,
    rgba(14, 165, 233, 0) 60%
  );
  transform: translateX(-86%) skewX(-14deg);
  animation: reasonGraphSweep 4.8s ease-in-out infinite;
}

@keyframes reasonPanelPulse {
  0% { opacity: 0.28; transform: scale(0.96); }
  70% { opacity: 0; transform: scale(1.06); }
  100% { opacity: 0; transform: scale(1.1); }
}

@keyframes reasonBeaconPulse {
  0% { opacity: 0.9; transform: scale(0.7); }
  100% { opacity: 0; transform: scale(1.6); }
}

@keyframes reasonFramePulse {
  0%, 100% { opacity: 0.45; }
  50% { opacity: 0.9; }
}

@keyframes reasonAmbientPulse {
  from { opacity: 0.55; }
  to { opacity: 0.95; }
}

@keyframes reasonGraphScanline {
  0% { transform: translateY(0); opacity: 0; }
  8% { opacity: 1; }
  48% { opacity: 0.95; }
  100% { transform: translateY(520px); opacity: 0; }
}

@keyframes reasonGraphSweep {
  0% { transform: translateX(-86%) skewX(-14deg); opacity: 0; }
  18% { opacity: 0.35; }
  52% { opacity: 0.95; }
  100% { transform: translateX(88%) skewX(-14deg); opacity: 0; }
}
</style>
