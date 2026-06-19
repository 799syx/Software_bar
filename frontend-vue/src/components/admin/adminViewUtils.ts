import type { Persona } from "../../types";

export type AdminTab = "screen" | "knowledge" | "persona" | "report";
export type ModalName = "knowledge" | "knowledgeDetail" | "spots" | "records" | "reportDetail" | "personaAdvanced" | null;
export type AdminAction =
  | "refresh"
  | "importPublic"
  | "importBehavior"
  | "uploadKnowledge"
  | "saveKnowledge"
  | "deleteKnowledge"
  | "convertChat"
  | "saveSpot"
  | "deleteSpot"
  | "savePersona";
export type ActionStatus = "idle" | "loading" | "success" | "error";

export type SpotForm = {
  id: number | null;
  name: string;
  description: string;
  story: string;
  tagsText: string;
  image: string;
  openTime: string;
  duration: number;
  popularity: number;
  location: string;
  mapZone: string;
  mapX: number | null;
  mapY: number | null;
  lat: number | null;
  lon: number | null;
  verifiedLocation: boolean;
  status: "active" | "inactive";
};

export type KnowledgeForm = {
  id: string | null;
  title: string;
  category: string;
  content: string;
  status: "active" | "inactive";
  sourceType: string;
  sourceFile: string;
  sourceSection: string;
};

export function readInitialAdminTab(): AdminTab {
  const tab = new URLSearchParams(window.location.search).get("adminTab");
  return tab === "knowledge" || tab === "persona" || tab === "report" ? tab : "screen";
}

export function readSessionAdminToken() {
  try {
    localStorage.removeItem("scenic_admin_token");
    return sessionStorage.getItem("scenic_admin_token") || "";
  } catch {
    return "";
  }
}

export function rememberSessionAdminToken(token: string) {
  try {
    if (token) {
      sessionStorage.setItem("scenic_admin_token", token);
    } else {
      sessionStorage.removeItem("scenic_admin_token");
    }
  } catch {
    // Some kiosk browsers disable storage; the in-memory token still works.
  }
}

export function clonePersona(persona: Persona): Persona {
  return { ...persona };
}

export function emptyKnowledgeForm(): KnowledgeForm {
  return {
    id: null,
    title: "",
    category: "景区知识",
    content: "",
    status: "active",
    sourceType: "manual",
    sourceFile: "",
    sourceSection: ""
  };
}

export function emptySpotForm(): SpotForm {
  return {
    id: null,
    name: "",
    description: "",
    story: "",
    tagsText: "佛教文化",
    image: "",
    openTime: "以景区公告为准",
    duration: 35,
    popularity: 80,
    location: "灵山胜境",
    mapZone: "lingshan",
    mapX: null,
    mapY: null,
    lat: null,
    lon: null,
    verifiedLocation: false,
    status: "active"
  };
}

export function formatNumber(value: number | undefined | null) {
  return Number(value || 0).toLocaleString("zh-CN");
}

export function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function percentNumber(value: number, total: number) {
  if (!total) return 0;
  return Math.round((Number(value || 0) / Math.max(Number(total || 0), 1)) * 100);
}

export function distributionCount(distribution: Record<string, number>, keywords: string[]) {
  return Object.entries(distribution || {}).reduce((total, [label, value]) => {
    const normalized = label.toLowerCase();
    return keywords.some((keyword) => normalized.includes(keyword.toLowerCase())) ? total + Number(value || 0) : total;
  }, 0);
}

export function compactTrendLabel(label: string) {
  if (/^\d{4}-\d{2}-\d{2}/.test(label)) return label.slice(5);
  if (label.length > 6) return label.slice(-6);
  return label;
}

export function compactText(text: string, maxLength: number) {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

export function pressurePercent(value: number, max: number) {
  if (!value) return "8%";
  return `${Math.max(8, Math.min(100, Math.round((value / Math.max(max, 1)) * 100)))}%`;
}

export function markdownTable(headers: string[], rows: Array<Array<string | number>>) {
  const header = `| ${headers.join(" | ")} |`;
  const separator = `| ${headers.map(() => "---").join(" | ")} |`;
  const body = rows.map((row) => `| ${row.map((cell) => String(cell).replace(/\|/g, "/")).join(" | ")} |`);
  return [header, separator, ...body].join("\n");
}
