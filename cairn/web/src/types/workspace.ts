export type ProjectStatus = 'active' | 'stopped' | 'completed';
export type SideTab = 'detail' | 'timeline' | 'hints' | 'intents';
export type LayoutMode = 'dagre_tb' | 'dagre_lr' | 'klay_tb' | 'klay_lr' | 'elk_tb' | 'elk_lr';

export interface ProjectReason {
  worker: string;
  trigger: string;
  started_at: string;
  last_heartbeat_at: string;
}

export interface ProjectMeta {
  id: string;
  title: string;
  status: ProjectStatus;
  created_at: string;
  reason: ProjectReason | null;
}

export interface ProjectSummary extends ProjectMeta {
  fact_count: number;
  intent_count: number;
  working_intent_count: number;
  unclaimed_intent_count: number;
  hint_count: number;
}

export interface Fact {
  id: string;
  description: string;
}

export interface Intent {
  id: string;
  from: string[];
  to: string | null;
  description: string;
  creator: string;
  worker: string | null;
  last_heartbeat_at: string | null;
  created_at: string;
  concluded_at: string | null;
}

export interface Hint {
  id: string;
  content: string;
  creator: string;
  created_at: string;
}

export interface ProjectDetail {
  project: ProjectMeta;
  facts: Fact[];
  intents: Intent[];
  hints: Hint[];
}

export interface CreateProjectRequest {
  title: string;
  origin: string;
  goal: string;
  hints?: Array<{ content: string; creator: string }>;
}

export interface CreateIntentRequest {
  from: string[];
  description: string;
  creator: string;
  worker?: string | null;
}

export interface CreateHintRequest {
  content: string;
  creator: string;
}

export interface ConcludeRequest {
  worker: string;
  description: string;
}

export interface ConcludeResponse {
  fact: Fact;
  intent: Intent;
}

export interface CompleteRequest {
  from: string[];
  description: string;
  worker: string;
}

export interface ReopenRequest {
  description: string;
  creator: string;
}

export interface ReopenResponse {
  project: ProjectMeta;
  fact: Fact;
  intent: Intent;
}

export interface CloneProjectRequest {
  title?: string | null;
}

export interface UpdateProjectTitleRequest {
  title: string;
}

export interface UpdateProjectStatusRequest {
  status: 'active' | 'stopped';
}

export interface HeartbeatRequest {
  worker: string;
}

export interface ExportFormatResponse {
  text: string;
}

export interface TimelineEntry {
  id: string;
  type:
    | 'project_created'
    | 'hint_added'
    | 'reason_started'
    | 'intent_running'
    | 'intent_declared'
    | 'intent_concluded'
    | 'project_completed';
  timestamp: string;
  actor: string;
  title: string;
  meta: string[];
  targetType: 'fact' | 'intent' | 'hint' | 'reason';
  targetId: string;
  order: number;
  intentId: string | null;
  producedFactId: string | null;
  sourceFactIds: string[];
  isLast?: boolean;
}

export interface ReplayFrame {
  event: TimelineEntry;
  project: ProjectDetail;
}

export interface ReplayState {
  active: boolean;
  playing: boolean;
  frameIndex: number;
  frames: ReplayFrame[];
  visibleEvents: TimelineEntry[];
  sourceProject: ProjectDetail | null;
  stepMs: number;
}

export interface WorkspacePrefs {
  actorName: string;
  layoutMode: LayoutMode;
  sidePanelWidth: number;
}
