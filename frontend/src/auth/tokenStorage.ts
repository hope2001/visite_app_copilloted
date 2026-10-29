const TOKEN_KEY = 'vmp.accessToken';

/** sessionStorage keeps the token scoped to the tab and cleared when the browser closes. */
export const tokenStorage = {
  get(): string | null {
    try {
      return window.sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string): void {
    try {
      window.sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      // Storage unavailable (private mode / quota): the session lasts until reload.
    }
  },
  clear(): void {
    try {
      window.sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      // Nothing to clear.
    }
  },
};
