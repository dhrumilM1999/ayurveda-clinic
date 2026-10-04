// Keeps an unsaved form (e.g. patient registration) in this browser tab, so nothing is lost if the
// page reloads or the user clicks away. Drafts live in sessionStorage: they disappear when the tab is
// closed, and logout removes them (patient details must not stay on a shared clinic computer).
const PREFIX = 'draft:';

export function saveDraft(key: string, data: unknown) {
  try {
    sessionStorage.setItem(PREFIX + key, JSON.stringify({ at: Date.now(), data }));
  } catch {
    // storage full or blocked: the form still works, only the draft is not kept
  }
}

export function loadDraft<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    return raw ? (JSON.parse(raw).data as T) : null;
  } catch {
    return null;
  }
}

export function clearDraft(key: string) {
  try {
    sessionStorage.removeItem(PREFIX + key);
  } catch {
    // ignore
  }
}

export function clearAllDrafts() {
  try {
    Object.keys(sessionStorage).filter((k) => k.startsWith(PREFIX)).forEach((k) => sessionStorage.removeItem(k));
  } catch {
    // ignore
  }
}
