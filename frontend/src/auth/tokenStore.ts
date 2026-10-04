// Keeps the login tokens and chosen branch in the browser.
// sessionStorage is cleared when the browser tab is closed (safer on shared clinic PCs).

const ACCESS = 'access_token';
const REFRESH = 'refresh_token';
const BRANCH = 'current_branch_id';

export const tokenStore = {
  getAccess: () => sessionStorage.getItem(ACCESS),
  getRefresh: () => sessionStorage.getItem(REFRESH),
  setTokens(access: string, refresh?: string) {
    sessionStorage.setItem(ACCESS, access);
    if (refresh) sessionStorage.setItem(REFRESH, refresh);
  },
  clear() {
    sessionStorage.removeItem(ACCESS);
    sessionStorage.removeItem(REFRESH);
  },
  // The branch is remembered across sessions so staff don't pick it every day.
  getBranch: () => localStorage.getItem(BRANCH),
  setBranch: (id: string) => localStorage.setItem(BRANCH, id),
};
