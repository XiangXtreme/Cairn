<script setup lang="ts">
import { Maximize2 } from 'lucide-vue-next';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

import AppButton from '@/components/ui/AppButton.vue';
import type { LayoutMode, ProjectDetail } from '@/types/workspace';
import {
  getFactRecord,
  factNodeSize,
  isBootstrapIntent,
  layoutDirection,
  layoutEngine,
  openIntentNodeLabel,
  openIntentNodeSize,
  openIntentNodeType,
  summarizeFactLabel,
} from '@/utils/workspace';

const props = defineProps<{
  project: ProjectDetail;
  layoutMode: LayoutMode;
  selectedNode?: { type: 'fact' | 'intent'; id: string } | null;
  selectedFacts: string[];
}>();

const emit = defineEmits<{
  selectFact: [factId: string];
  selectIntent: [intentId: string];
  clear: [];
  layout: [mode: LayoutMode];
}>();

const container = ref<HTMLDivElement | null>(null);
let cy: any = null;

const layoutModes: Array<{ id: LayoutMode; label: string }> = [
  { id: 'dagre_tb', label: 'Dagre TB' },
  { id: 'dagre_lr', label: 'Dagre LR' },
  { id: 'klay_tb', label: 'Klay TB' },
  { id: 'klay_lr', label: 'Klay LR' },
  { id: 'elk_tb', label: 'ELK TB' },
  { id: 'elk_lr', label: 'ELK LR' },
];

const headerLabel = computed(() => {
  const engine = layoutEngine(props.layoutMode).toUpperCase();
  return `${engine} / ${layoutDirection(props.layoutMode)}`;
});

function buildElements() {
  const nodes: any[] = [];
  const edges: any[] = [];
  for (const fact of props.project.facts) {
    const nodeType = fact.id === 'origin' ? 'origin' : fact.id === 'goal' ? 'goal' : 'fact';
    const label = summarizeFactLabel(fact);
    const size = factNodeSize(label, nodeType);
    nodes.push({
      data: {
        id: fact.id,
        label,
        description: fact.description,
        nodeType,
        width: size.width,
        height: size.height,
      },
    });
  }
  for (const intent of props.project.intents) {
    if (intent.to) {
      for (const sourceId of intent.from) {
        edges.push({
          data: {
            id: `${intent.id}_${sourceId}`,
            source: sourceId,
            target: intent.to,
            intentId: intent.id,
            label: intent.description,
            status: 'concluded',
          },
        });
      }
      continue;
    }

    const placeholderId = `_ph_${intent.id}`;
    const size = openIntentNodeSize(intent);
    const nodeType = openIntentNodeType(intent);
    nodes.push({
      data: {
        id: placeholderId,
        label: openIntentNodeLabel(intent),
        description: intent.description,
        intentId: intent.id,
        nodeType,
        width: size.width,
        height: size.height,
      },
    });
    for (const sourceId of intent.from) {
      edges.push({
        data: {
          id: `${intent.id}_${sourceId}`,
          source: sourceId,
          target: placeholderId,
          intentId: intent.id,
          label: intent.description,
          status: nodeType,
        },
      });
    }
  }
  return [...nodes, ...edges];
}

function graphStyle() {
  return [
    {
      selector: 'node',
      style: {
        shape: 'round-rectangle',
        label: 'data(label)',
        color: '#fff',
        'font-size': '10px',
        'font-weight': 700,
        'text-wrap': 'wrap',
        'text-max-width': '118px',
        width: 'data(width)',
        height: 'data(height)',
        'text-valign': 'center',
        'text-halign': 'center',
        'border-width': 0,
      },
    },
    { selector: 'node[nodeType="origin"]', style: { 'background-color': '#0f766e' } },
    { selector: 'node[nodeType="goal"]', style: { 'background-color': '#e11d48' } },
    { selector: 'node[nodeType="fact"]', style: { 'background-color': '#4f46e5' } },
    { selector: 'node[nodeType="unclaimed"]', style: { shape: 'ellipse', 'background-color': '#cbd5e1', color: '#64748b', width: 20, height: 20, 'border-width': 1.5, 'border-color': '#94a3b8', 'border-style': 'dashed' } },
    { selector: 'node[nodeType="in_progress"]', style: { shape: 'ellipse', 'background-color': '#f59e0b', width: 22, height: 22, 'border-width': 2, 'border-color': '#d97706' } },
    { selector: 'node[nodeType="bootstrap_pending"]', style: { 'background-color': '#fff7ed', color: '#c2410c', 'border-width': 1.5, 'border-color': '#fdba74', 'border-style': 'dashed' } },
    { selector: 'node[nodeType="bootstrap_running"]', style: { 'background-color': '#fb923c', 'border-width': 2, 'border-color': '#ea580c' } },
    {
      selector: 'edge',
      style: {
        width: 2,
        'curve-style': 'bezier',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.8,
        label: 'data(label)',
        'font-size': '7px',
        color: '#64748b',
        'text-rotation': 'autorotate',
        'text-margin-y': -9,
        'text-background-color': '#f8fafc',
        'text-background-opacity': 0.86,
        'text-background-padding': '2px',
      },
    },
    { selector: 'edge[status="concluded"]', style: { 'line-color': '#6ee7b7', 'target-arrow-color': '#6ee7b7' } },
    { selector: 'edge[status="unclaimed"]', style: { 'line-color': '#cbd5e1', 'target-arrow-color': '#cbd5e1', 'line-style': 'dashed' } },
    { selector: 'edge[status="in_progress"]', style: { 'line-color': '#fbbf24', 'target-arrow-color': '#fbbf24', 'line-style': 'dashed' } },
    { selector: 'edge[status="bootstrap_pending"]', style: { 'line-color': '#fdba74', 'target-arrow-color': '#fdba74', 'line-style': 'dashed' } },
    { selector: 'edge[status="bootstrap_running"]', style: { 'line-color': '#fb923c', 'target-arrow-color': '#fb923c', 'line-style': 'dashed' } },
    { selector: '.selected', style: { 'border-width': 4, 'border-color': '#312e81', 'underlay-color': '#c7d2fe', 'underlay-padding': 8, 'underlay-opacity': 0.5 } },
    { selector: '.faded', style: { opacity: 0.38 } },
  ];
}

function layoutOptions(animate = true) {
  const direction = layoutDirection(props.layoutMode);
  const engine = layoutEngine(props.layoutMode);
  if (engine === 'elk') {
    return {
      name: 'elk',
      fit: true,
      padding: 48,
      animate,
      animationDuration: 300,
      elk: {
        algorithm: 'layered',
        'elk.direction': direction === 'TB' ? 'DOWN' : 'RIGHT',
        'elk.layered.spacing.nodeNodeBetweenLayers': '80',
        'elk.spacing.nodeNode': '40',
      },
    };
  }
  if (engine === 'klay') {
    return {
      name: 'klay',
      fit: true,
      padding: 48,
      animate,
      animationDuration: 300,
      klay: {
        direction: direction === 'TB' ? 'DOWN' : 'RIGHT',
        spacing: 48,
        thoroughness: 6,
      },
    };
  }
  return {
    name: 'dagre',
    rankDir: direction,
    nodeSep: 56,
    rankSep: 76,
    fit: true,
    padding: 48,
    animate,
    animationDuration: 300,
  };
}

function registerPlugins() {
  if (!window.cytoscape) return;
  if (window.cytoscapeDagre) window.cytoscape.use(window.cytoscapeDagre);
  if (window.cytoscapeKlay) window.cytoscape.use(window.cytoscapeKlay(window.klay));
  if (window.cytoscapeElk) window.cytoscape.use(window.cytoscapeElk);
}

function applySelection() {
  if (!cy) return;
  cy.elements().removeClass('selected faded');
  if (!props.selectedNode && props.selectedFacts.length === 0) return;
  const selectedIds = new Set<string>();
  const selectedEdgeIds = new Set<string>();

  function collectIntentElements(intentId: string) {
    const intent = props.project.intents.find((item) => item.id === intentId);
    if (!intent) return;
    if (intent.to) selectedIds.add(intent.to);
    else selectedIds.add(`_ph_${intent.id}`);
    for (const sourceId of intent.from) {
      selectedIds.add(sourceId);
      selectedEdgeIds.add(`${intent.id}_${sourceId}`);
    }
    if (isBootstrapIntent(intent)) {
      selectedIds.add('goal');
      selectedEdgeIds.add(`${intent.id}_goal`);
    }
  }

  function collectFactLineage(factId: string, factSeen = new Set<string>(), intentSeen = new Set<string>()) {
    if (factSeen.has(factId)) return;
    factSeen.add(factId);
    selectedIds.add(factId);
    for (const intent of props.project.intents) {
      if (intent.to !== factId) continue;
      if (!intentSeen.has(intent.id)) {
        intentSeen.add(intent.id);
        collectIntentElements(intent.id);
        for (const sourceId of intent.from) collectFactLineage(sourceId, factSeen, intentSeen);
      }
    }
  }

  if (props.selectedNode?.type === 'fact') collectFactLineage(props.selectedNode.id);
  if (props.selectedNode?.type === 'intent') {
    collectIntentElements(props.selectedNode.id);
  }
  for (const factId of props.selectedFacts) selectedIds.add(factId);
  cy.edges().forEach((edge: any) => {
    if (selectedEdgeIds.has(edge.id())) edge.addClass('selected');
    else if (selectedIds.has(edge.source().id()) && selectedIds.has(edge.target().id())) edge.addClass('selected');
    else if (selectedIds.size > 0) edge.addClass('faded');
  });
  cy.nodes().forEach((node: any) => {
    if (selectedIds.has(node.id())) node.addClass('selected');
    else if (selectedIds.size > 0) node.addClass('faded');
  });
}

function createGraph() {
  if (!container.value || !window.cytoscape) return;
  registerPlugins();
  cy = window.cytoscape({
    container: container.value,
    elements: buildElements(),
    style: graphStyle(),
    layout: layoutOptions(false),
    minZoom: 0.15,
    maxZoom: 3.2,
  });
  cy.on('tap', 'node', (event: any) => {
    const data = event.target.data();
    if (data.intentId) emit('selectIntent', data.intentId);
    else emit('selectFact', data.id);
  });
  cy.on('tap', 'edge', (event: any) => {
    const intentId = event.target.data('intentId');
    if (intentId) emit('selectIntent', intentId);
  });
  cy.on('tap', (event: any) => {
    if (event.target === cy) emit('clear');
  });
  applySelection();
}

function rebuild() {
  if (!cy) {
    createGraph();
    return;
  }
  cy.json({ elements: buildElements() });
  cy.layout(layoutOptions()).run();
  applySelection();
}

function fitGraph() {
  if (cy) cy.fit(undefined, 48);
}

function centerOnSelection() {
  if (!cy || !props.selectedNode) return;
  if (props.selectedNode.type === 'fact') {
    const node = cy.getElementById(props.selectedNode.id);
    if (node.length > 0) cy.animate({ center: { eles: node } }, { duration: 180 });
    return;
  }
  const intentElements = cy.edges(`[intentId="${props.selectedNode.id}"]`);
  if (intentElements.length > 0) cy.animate({ fit: { eles: intentElements.connectedNodes().union(intentElements), padding: 80 } }, { duration: 220 });
}

onMounted(() => {
  createGraph();
});

onBeforeUnmount(() => {
  if (cy) cy.destroy();
  cy = null;
});

watch(() => props.project, rebuild, { deep: true });
watch(() => props.layoutMode, () => {
  if (cy) cy.layout(layoutOptions()).run();
});
watch(() => [props.selectedNode, props.selectedFacts], () => {
  applySelection();
  centerOnSelection();
}, { deep: true });
</script>

<template>
  <section class="rounded-[28px] border border-slate-200 bg-white shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
      <div>
        <div class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Graph</div>
        <div class="mt-1 text-sm font-medium text-slate-900">{{ headerLabel }}</div>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          v-for="mode in layoutModes"
          :key="mode.id"
          type="button"
          class="rounded-2xl px-3 py-1.5 text-xs font-medium transition"
          :class="layoutMode === mode.id ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          @click="emit('layout', mode.id)"
        >
          {{ mode.label }}
        </button>
        <AppButton :icon="Maximize2" size="sm" @click="fitGraph">Fit</AppButton>
      </div>
    </div>
    <div ref="container" class="h-[620px] w-full rounded-b-[28px] bg-[radial-gradient(circle_at_top,_rgba(148,163,184,0.14),_transparent_55%)]" />
  </section>
</template>
