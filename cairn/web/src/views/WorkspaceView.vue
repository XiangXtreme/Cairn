<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { computed, onMounted, onUnmounted, reactive } from 'vue';

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
import { useProjectStore } from '@/stores/project';
import { useWorkspaceStore } from '@/stores/workspace';
import { useWorkspaceUiStore } from '@/stores/workspaceUi';

const workspace = useWorkspaceStore();
const projectStore = useProjectStore();
const workspaceUi = useWorkspaceUiStore();

const workspaceRefs = storeToRefs(workspace);
const projectRefs = storeToRefs(projectStore);
const workspaceUiRefs = storeToRefs(workspaceUi);

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

const currentRouteProjectId = computed(() => {
  const hash = window.location.hash || '#/';
  const match = hash.match(/^#\/projects\/(.+)$/);
  return match ? decodeURIComponent(match[1]) : '';
});

const selectedProjectTitle = computed(() => projectRefs.project.value?.project.title || '');
const selectedFactId = computed(() => (projectRefs.selectedNode.value?.type === 'fact' ? projectRefs.selectedNode.value.id : null));
const selectedIntentId = computed(() => (projectRefs.selectedNode.value?.type === 'intent' ? projectRefs.selectedNode.value.id : null));

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
  if (projectId && projectRefs.project.value?.project.id !== projectId) {
    workspace.setSelectedProject(projectId);
    window.location.hash = `#/projects/${encodeURIComponent(projectId)}`;
  }
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
  const cloned = await projectStore.cloneProject(forms.clone.title);
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
  const deletingId = projectRefs.project.value?.project.id || workspace.selectedProjectId;
  await projectStore.deleteProject();
  workspace.removeProject(deletingId);
  workspaceUi.closeModal();
  goHome();
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
  void syncRoute();
}

onMounted(async () => {
  window.addEventListener('hashchange', onHashChange);
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
        @delete="askDelete"
      />

      <section v-if="projectRefs.project.value" class="grid grid-cols-1 gap-5 2xl:grid-cols-[minmax(0,1fr)_380px]">
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

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'create'" title="新建项目" description="输入 origin / goal，新的 Vue workspace 会直接打开项目详情。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="项目标题"><TextInput v-model="forms.create.title" /></FormField>
        <FormField label="Origin"><textarea v-model="forms.create.origin" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <FormField label="Goal"><textarea v-model="forms.create.goal" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <FormField label="初始 Hint"><textarea v-model="forms.create.hint" class="min-h-24 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
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

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'hint'" title="添加 Hint" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="Hint"><textarea v-model="forms.hint.content" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitHint">添加</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'intent'" title="新增 Intent" description="当前使用右侧已选中的事实作为来源。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="Description"><textarea v-model="forms.intent.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="text-xs text-slate-400">来源：{{ projectRefs.selectedFacts.value.join(', ') || '未选择 facts' }}</div>
        <div class="flex justify-end"><AppButton variant="brand" :disabled="projectRefs.selectedFacts.value.length === 0" @click="submitIntent">创建 Intent</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'complete'" title="完成项目" description="使用当前选中的 facts 作为完成来源。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="完成说明"><textarea v-model="forms.complete.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="text-xs text-slate-400">来源：{{ projectRefs.selectedFacts.value.join(', ') || '未选择 facts' }}</div>
        <div class="flex justify-end"><AppButton variant="brand" :disabled="projectRefs.selectedFacts.value.length === 0" @click="submitComplete">标记完成</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'reopen'" title="Reopen 项目" description="为已完成项目注入新的外部反馈事实。" @close="closeModal">
      <div class="space-y-4 p-5">
        <FormField label="反馈描述"><textarea v-model="forms.reopen.description" class="min-h-28 w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100" /></FormField>
        <div class="flex justify-end"><AppButton variant="brand" @click="submitReopen">Reopen</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'delete'" title="删除项目" description="这个动作会删除数据库记录和运行时产物。" @close="closeModal">
      <div class="space-y-4 p-5">
        <p class="text-sm text-slate-600">确认删除当前项目？这个动作不可撤销。</p>
        <div class="flex justify-end"><AppButton variant="danger" @click="submitDelete">确认删除</AppButton></div>
      </div>
    </ModalShell>

    <ModalShell v-if="workspaceUiRefs.activeModal.value === 'conclude'" title="提交结论" description="为当前已认领的 intent 生成新的 fact。" @close="closeModal">
      <div class="space-y-4 p-5">
        <div class="text-xs text-slate-400">Intent：{{ workspaceUiRefs.pendingIntentId.value || selectedIntentId }}</div>
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
