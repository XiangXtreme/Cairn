import type {
  Fact,
  Intent,
  LayoutMode,
  ProjectDetail,
  ProjectStatus,
  ReplayFrame,
  ReplayState,
  RunningState,
  TimelineEntry,
  WorkspacePrefs,
} from '@/types/workspace';

export const DEFAULT_PREFS: WorkspacePrefs = {
  actorName: 'Human',
  layoutMode: 'dagre_tb',
  sidePanelWidth: 360,
};

export function isValidLayoutMode(mode: string): mode is LayoutMode {
  return ['dagre_tb', 'dagre_lr', 'klay_tb', 'klay_lr', 'elk_tb', 'elk_lr'].includes(mode);
}

export function loadWorkspacePrefs(): WorkspacePrefs {
  try {
    const raw = window.localStorage.getItem('cairn.localPrefs');
    const panelRaw = window.localStorage.getItem('cairn.sidePanelWidth');
    const next = { ...DEFAULT_PREFS };
    if (raw) {
      const parsed = JSON.parse(raw) as { actor_name?: string; layout_mode?: string; layout_dir?: string };
      if (parsed.actor_name?.trim()) next.actorName = parsed.actor_name.trim();
      if (parsed.layout_mode && isValidLayoutMode(parsed.layout_mode)) next.layoutMode = parsed.layout_mode;
      else if (parsed.layout_dir === 'LR') next.layoutMode = 'dagre_lr';
      else if (parsed.layout_dir === 'TB') next.layoutMode = 'dagre_tb';
    }
    const panel = Number(panelRaw);
    if (Number.isFinite(panel) && panel >= 280 && panel <= 720) next.sidePanelWidth = panel;
    return next;
  } catch {
    return { ...DEFAULT_PREFS };
  }
}

export function persistWorkspacePrefs(prefs: WorkspacePrefs) {
  window.localStorage.setItem(
    'cairn.localPrefs',
    JSON.stringify({ actor_name: prefs.actorName, layout_mode: prefs.layoutMode }),
  );
  window.localStorage.setItem('cairn.sidePanelWidth', String(prefs.sidePanelWidth));
}

export function projectStatusTone(status: ProjectStatus) {
  if (status === 'active') return 'teal';
  if (status === 'stopped') return 'amber';
  return 'slate';
}

export function projectStatusLabel(status: ProjectStatus) {
  if (status === 'active') return '活跃';
  if (status === 'stopped') return '暂停';
  return '完成';
}

export function layoutEngine(mode: LayoutMode) {
  if (mode.startsWith('elk')) return 'elk';
  if (mode.startsWith('klay')) return 'klay';
  return 'dagre';
}

export function layoutDirection(mode: LayoutMode) {
  return mode.endsWith('_lr') ? 'LR' : 'TB';
}

export function summarizeFactLabel(fact: Fact) {
  if (fact.id === 'origin') return '起点';
  if (fact.id === 'goal') return '目标';
  const normalized = fact.description.replace(/\s+/g, ' ').trim();
  return Array.from(normalized).length <= 24 ? normalized || fact.id : `${Array.from(normalized).slice(0, 24).join('')}…`;
}

export function factNodeSize(label: string, nodeType: 'origin' | 'goal' | 'fact') {
  const length = Math.max(4, Array.from(label).length);
  const width = Math.min(nodeType === 'fact' ? 132 : 112, Math.max(74, length * 7.4));
  const height = nodeType === 'fact' ? 46 : 40;
  return { width, height };
}

export function isBootstrapIntent(intent: Intent) {
  return Boolean(
    intent.description === 'bootstrap'
      && intent.creator === 'dispatcher.bootstrap'
      && intent.from.length === 1
      && intent.from[0] === 'origin'
      && intent.to === null,
  );
}

export function openIntentNodeType(intent: Intent) {
  if (isBootstrapIntent(intent)) return intent.worker ? 'bootstrap_running' : 'bootstrap_pending';
  return intent.worker ? 'in_progress' : 'unclaimed';
}

export function openIntentNodeLabel(intent: Intent) {
  return isBootstrapIntent(intent) ? '启动' : '?';
}

export function openIntentNodeSize(intent: Intent) {
  return isBootstrapIntent(intent) ? { width: 82, height: 30 } : { width: 22, height: 22 };
}

export function getFactRecord(project: ProjectDetail | null, factId: string) {
  return project?.facts.find((fact) => fact.id === factId) || null;
}

export function getProjectRunningState(project: ProjectDetail | null): RunningState | null {
  if (!project) return null;
  if (project.project.reason) {
    return {
      worker: project.project.reason.worker,
      trigger: project.project.reason.trigger,
      started_at: project.project.reason.started_at,
      last_heartbeat_at: project.project.reason.last_heartbeat_at,
    };
  }
  const runningIntent = project.intents
    .filter((intent) => !intent.concluded_at && intent.worker)
    .sort((left, right) => (right.last_heartbeat_at || '').localeCompare(left.last_heartbeat_at || ''))[0];
  if (!runningIntent?.worker) return null;
  return {
    worker: runningIntent.worker,
    trigger: isBootstrapIntent(runningIntent) ? 'bootstrap' : runningIntent.description,
    started_at: runningIntent.created_at,
    last_heartbeat_at: runningIntent.last_heartbeat_at || runningIntent.created_at,
  };
}

export function buildTimeline(project: ProjectDetail | null): TimelineEntry[] {
  if (!project) return [];
  const events: TimelineEntry[] = [];
  let order = 0;
  const origin = getFactRecord(project, 'origin');
  const goal = getFactRecord(project, 'goal');

  events.push({
    id: `project-created-${project.project.id}`,
    type: 'project_created',
    timestamp: project.project.created_at,
    actor: 'system',
    title: project.project.title,
    meta: [origin?.description, goal ? `goal: ${goal.description}` : null].filter(Boolean) as string[],
    targetType: 'fact',
    targetId: 'origin',
    order: order++,
    intentId: null,
    producedFactId: null,
    sourceFactIds: [],
  });

  for (const hint of project.hints) {
    events.push({
      id: `hint-${hint.id}`,
      type: 'hint_added',
      timestamp: hint.created_at,
      actor: hint.creator,
      title: hint.content,
      meta: [],
      targetType: 'hint',
      targetId: hint.id,
      order: order++,
      intentId: null,
      producedFactId: null,
      sourceFactIds: [],
    });
  }

  for (const intent of project.intents) {
    events.push({
      id: `intent-declared-${intent.id}`,
      type: 'intent_declared',
      timestamp: intent.created_at,
      actor: intent.creator,
      title: intent.description,
      meta: [intent.id, `来源 ${intent.from.join(', ')}`],
      targetType: 'intent',
      targetId: intent.id,
      order: order++,
      intentId: intent.id,
      producedFactId: null,
      sourceFactIds: [...intent.from],
    });

    if (!intent.concluded_at || !intent.to) continue;

    if (intent.to === 'goal') {
      events.push({
        id: `project-completed-${intent.id}`,
        type: 'project_completed',
        timestamp: intent.concluded_at,
        actor: intent.worker || intent.creator,
        title: intent.description,
        meta: [intent.id, `来源 ${intent.from.join(', ')}`],
        targetType: 'fact',
        targetId: 'goal',
        order: order++,
        intentId: intent.id,
        producedFactId: 'goal',
        sourceFactIds: [...intent.from],
      });
      continue;
    }

    const fact = getFactRecord(project, intent.to);
    events.push({
      id: `intent-concluded-${intent.id}`,
      type: 'intent_concluded',
      timestamp: intent.concluded_at,
      actor: intent.worker || intent.creator,
      title: fact ? fact.description : intent.description,
      meta: [intent.id, `产出 ${intent.to}`, `来源 ${intent.from.join(', ')}`],
      targetType: 'fact',
      targetId: intent.to,
      order: order++,
      intentId: intent.id,
      producedFactId: intent.to,
      sourceFactIds: [...intent.from],
    });
  }

  return [...events]
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp) || a.order - b.order)
    .map((entry, index, list) => ({ ...entry, isLast: index === list.length - 1 }));
}

export function cloneProjectDetail(project: ProjectDetail): ProjectDetail {
  return JSON.parse(JSON.stringify(project)) as ProjectDetail;
}

export function buildInitialReplayProject(sourceProject: ProjectDetail): ProjectDetail {
  const origin = sourceProject.facts.find((fact) => fact.id === 'origin');
  const goal = sourceProject.facts.find((fact) => fact.id === 'goal');
  return {
    project: {
      ...cloneProjectDetail(sourceProject).project,
      status: 'active',
      reason: null,
    },
    facts: [origin, goal].filter(Boolean).map((fact) => JSON.parse(JSON.stringify(fact))) as Fact[],
    intents: [],
    hints: [],
  };
}

export function replayEventDurationMs(event?: TimelineEntry | null, fallback = 1100) {
  if (!event) return fallback;
  if (event.type === 'hint_added') return Math.round(fallback * 0.8);
  if (event.type === 'reason_started') return Math.round(fallback * 0.9);
  if (event.type === 'intent_running') return Math.round(fallback * 0.85);
  if (event.type === 'project_completed') return Math.round(fallback * 1.2);
  return fallback;
}

export function buildReplayFrames(sourceProject: ProjectDetail, baseEvents: TimelineEntry[]): ReplayFrame[] {
  const sourceIntents = new Map(sourceProject.intents.map((intent) => [intent.id, intent]));
  const replayEvents: TimelineEntry[] = [];

  for (const event of baseEvents) {
    if (event.type !== 'intent_declared' || !event.intentId) {
      replayEvents.push(JSON.parse(JSON.stringify(event)));
      continue;
    }

    const sourceIntent = sourceIntents.get(event.intentId);
    replayEvents.push({
      id: `reason-started-${event.intentId}`,
      type: 'reason_started',
      timestamp: sourceIntent?.created_at || event.timestamp,
      actor: sourceIntent?.creator || event.actor || 'reasoner',
      title: sourceIntent?.description || event.title,
      meta: [
        sourceIntent?.id || event.intentId,
        `来源 ${(sourceIntent?.from || event.sourceFactIds || []).join(', ')}`,
      ],
      targetType: 'reason',
      targetId: sourceIntent?.id || event.intentId,
      order: event.order - 0.2,
      intentId: sourceIntent?.id || event.intentId,
      producedFactId: null,
      sourceFactIds: [...(sourceIntent?.from || event.sourceFactIds || [])],
    });
    replayEvents.push(JSON.parse(JSON.stringify(event)));
    if (!sourceIntent?.worker) continue;
    replayEvents.push({
      id: `intent-running-${sourceIntent.id}`,
      type: 'intent_running',
      timestamp: sourceIntent.last_heartbeat_at || sourceIntent.created_at,
      actor: sourceIntent.worker,
      title: sourceIntent.description,
      meta: [sourceIntent.id, `Worker ${sourceIntent.worker}`],
      targetType: 'intent',
      targetId: sourceIntent.id,
      order: event.order + 0.2,
      intentId: sourceIntent.id,
      producedFactId: null,
      sourceFactIds: [...sourceIntent.from],
    });
  }

  const replayProject = buildInitialReplayProject(sourceProject);
  const frames: ReplayFrame[] = [];
  for (const event of replayEvents) {
    applyReplayEvent(replayProject, sourceProject, event);
    frames.push({
      event: JSON.parse(JSON.stringify(event)),
      project: cloneProjectDetail(replayProject),
    });
  }

  if (frames.length > 0) {
    frames[frames.length - 1].project.project.status = sourceProject.project.status;
    frames[frames.length - 1].project.project.reason = sourceProject.project.reason
      ? JSON.parse(JSON.stringify(sourceProject.project.reason))
      : null;
  }
  return frames;
}

export function applyReplayEvent(replayProject: ProjectDetail, sourceProject: ProjectDetail, event: TimelineEntry) {
  const sourceIntent = event.intentId
    ? sourceProject.intents.find((intent) => intent.id === event.intentId) || null
    : null;

  if (event.type === 'project_created') {
    replayProject.project.title = sourceProject.project.title;
    replayProject.project.status = 'active';
    return;
  }

  if (event.type === 'hint_added') {
    const hint = sourceProject.hints.find((item) => item.id === event.targetId);
    if (hint && !replayProject.hints.some((item) => item.id === hint.id)) {
      replayProject.hints.push(JSON.parse(JSON.stringify(hint)));
    }
    return;
  }

  if (event.type === 'reason_started') {
    replayProject.project.reason = {
      worker: event.actor || 'reasoner',
      trigger: 'new_facts',
      started_at: event.timestamp,
      last_heartbeat_at: event.timestamp,
    };
    return;
  }

  if (event.type === 'intent_declared') {
    if (!sourceIntent) return;
    replayProject.project.reason = null;
    if (!replayProject.intents.some((intent) => intent.id === sourceIntent.id)) {
      replayProject.intents.push({
        id: sourceIntent.id,
        from: [...sourceIntent.from],
        to: null,
        description: sourceIntent.description,
        creator: sourceIntent.creator,
        worker: null,
        last_heartbeat_at: null,
        created_at: sourceIntent.created_at,
        concluded_at: null,
      });
    }
    return;
  }

  if (event.type === 'intent_running') {
    if (!sourceIntent) return;
    const replayIntent = replayProject.intents.find((intent) => intent.id === sourceIntent.id);
    if (!replayIntent) return;
    replayIntent.worker = sourceIntent.worker || sourceIntent.creator;
    replayIntent.last_heartbeat_at = sourceIntent.last_heartbeat_at || sourceIntent.created_at;
    return;
  }

  if (event.type !== 'intent_concluded' && event.type !== 'project_completed') return;
  if (!sourceIntent) return;

  const replayIntent = replayProject.intents.find((intent) => intent.id === sourceIntent.id);
  if (replayIntent) {
    replayIntent.to = sourceIntent.to;
    replayIntent.worker = sourceIntent.worker || sourceIntent.creator;
    replayIntent.last_heartbeat_at = sourceIntent.last_heartbeat_at;
    replayIntent.concluded_at = sourceIntent.concluded_at;
  }

  if (event.type === 'project_completed') {
    replayProject.project.status = 'completed';
    return;
  }

  const producedFact = sourceProject.facts.find((fact) => fact.id === sourceIntent.to);
  if (producedFact && !replayProject.facts.some((fact) => fact.id === producedFact.id)) {
    replayProject.facts.push(JSON.parse(JSON.stringify(producedFact)));
  }
}

export function createEmptyReplayState(stepMs = 1100): ReplayState {
  return {
    active: false,
    playing: false,
    frameIndex: -1,
    frames: [],
    visibleEvents: [],
    sourceProject: null,
    stepMs,
  };
}
