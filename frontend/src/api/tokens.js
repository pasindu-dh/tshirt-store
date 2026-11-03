const STORAGE_KEY = "furzy-auth";

export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredAuth(auth) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
  } catch {
    // Storage can be unavailable (e.g. private mode); the session still works in memory.
  }
}

export function clearStoredAuth() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore unavailable storage.
  }
}

export function getAccessToken() {
  return getStoredAuth()?.access_token ?? null;
}
