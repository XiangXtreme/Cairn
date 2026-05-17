export type CairnTitleBadgeKind =
  | "bootstrap"
  | "plan"
  | "explore"
  | "fact"
  | "done";

export interface CairnTitleBadge {
  kind: CairnTitleBadgeKind;
  label: string;
  text: string;
}

const CAIRN_PREFIXES: Array<{
  prefix: string;
  kind: CairnTitleBadgeKind;
  label: string;
}> = [
  { prefix: "起步: ", kind: "bootstrap", label: "起步" },
  { prefix: "计划: ", kind: "plan", label: "计划" },
  { prefix: "探索: ", kind: "explore", label: "探索" },
  { prefix: "事实: ", kind: "fact", label: "事实" },
  { prefix: "完成: ", kind: "done", label: "完成" },
];

export function parseCairnTitleBadge(
  project: string,
  title: string,
  isShell: boolean,
): CairnTitleBadge | null {
  if (isShell || !project.startsWith("cairn:")) return null;
  for (const item of CAIRN_PREFIXES) {
    if (!title.startsWith(item.prefix)) continue;
    return {
      kind: item.kind,
      label: item.label,
      text: title.slice(item.prefix.length).trim() || title,
    };
  }
  return null;
}
