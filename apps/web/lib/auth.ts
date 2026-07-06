export interface AuthSession {
  accessToken: string;
  userEmail: string;
}

export interface ScopeSelection {
  organizationId: string;
  brandId: string | null;
}

const SESSION_STORAGE_KEY = 'cf-auth-session';
const SCOPE_STORAGE_KEY = 'cf-scope-selection';

function canUseStorage(): boolean {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

export function saveSession(session: AuthSession): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function loadSession(): AuthSession | null {
  if (!canUseStorage()) {
    return null;
  }

  const raw = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<AuthSession>;
    if (!parsed.accessToken || !parsed.userEmail) {
      return null;
    }
    return { accessToken: parsed.accessToken, userEmail: parsed.userEmail };
  } catch {
    return null;
  }
}

export function clearSession(): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.removeItem(SESSION_STORAGE_KEY);
}

export function saveScopeSelection(selection: ScopeSelection): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.setItem(SCOPE_STORAGE_KEY, JSON.stringify(selection));
}

export function loadScopeSelection(): ScopeSelection | null {
  if (!canUseStorage()) {
    return null;
  }

  const raw = window.localStorage.getItem(SCOPE_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<ScopeSelection>;
    if (!parsed.organizationId) {
      return null;
    }
    return {
      organizationId: parsed.organizationId,
      brandId: parsed.brandId ?? null,
    };
  } catch {
    return null;
  }
}

export function clearScopeSelection(): void {
  if (!canUseStorage()) {
    return;
  }
  window.localStorage.removeItem(SCOPE_STORAGE_KEY);
}
