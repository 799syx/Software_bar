import type { Persona } from "../types";

const STORAGE_KEY = "scenic-admin-persona-draft";

export function savePersonaDraft(persona: Persona) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(persona));
  } catch {
    // ignore quota / private mode
  }
}

export function loadPersonaDraft(): Persona | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Persona;
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

export function clearPersonaDraft() {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
