// Remembers who is logged in, which branch is chosen, and what they are allowed to do.
// ASK FIRST before editing.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setSessionExpiredHandler } from '../api/client';
import type { AdditionalFeature, FeatureFlag, Me, MyBranch } from '../api/types';
import i18n, { setLanguage } from '../i18n';
import { clearAllDrafts } from '../utils/formDraft';
import { tokenStore } from './tokenStore';

interface AuthValue {
  me: Me | null;
  loading: boolean;
  branch: MyBranch | null;
  /** Module switches of the branch plus the organization's additional features: {code: on/off} */
  features: Record<string, boolean>;
  /** Is this optional additional feature switched on (Additional settings)? */
  hasFeature: (code: string) => boolean;
  /** Load the switches again (after changing them). */
  reloadFeatures: () => Promise<void>;
  /** Does the user have this permission in the current branch? */
  can: (code: string) => boolean;
  completeLogin: (access: string, refresh: string) => Promise<void>;
  switchBranch: (branchId: string) => void;
  logout: (reason?: 'idle' | 'expired') => Promise<void>;
  logoutReason: string | null;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [branchId, setBranchId] = useState<string | null>(tokenStore.getBranch());
  const [features, setFeatures] = useState<Record<string, boolean>>({});
  const [logoutReason, setLogoutReason] = useState<string | null>(null);

  const loadMe = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get<Me>('/auth/me/');
      setMe(data);
      // Keep the saved branch if still allowed, otherwise use the first one.
      const saved = tokenStore.getBranch();
      const chosen = data.branches.find((b) => b.id === saved) ?? data.branches[0];
      if (chosen) {
        tokenStore.setBranch(chosen.id);
        setBranchId(chosen.id);
      }
      if (!localStorage.getItem('language') && data.user.preferred_language) {
        setLanguage(data.user.preferred_language);
      }
    } catch {
      tokenStore.clear();
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  // Load the module on/off switches (branch) and the additional features (organization).
  const reloadFeatures = useCallback(async () => {
    try {
      const [modules, extras] = await Promise.all([
        api.get<FeatureFlag[]>('/feature-flags/'),
        api.get<AdditionalFeature[]>('/additional-features/'),
      ]);
      setFeatures(Object.fromEntries([...modules.data, ...extras.data].map((f) => [f.code, f.enabled])));
    } catch {
      setFeatures({});
    }
  }, []);

  // ...whenever the branch changes.
  useEffect(() => {
    if (!me || !branchId) return;
    reloadFeatures();
  }, [me, branchId, reloadFeatures]);
  const hasFeature = useCallback((code: string) => features[code] === true, [features]);

  const logout = useCallback(async (reason?: 'idle' | 'expired') => {
    const refresh = tokenStore.getRefresh();
    if (refresh) {
      try {
        await api.post('/auth/logout/', { refresh });
      } catch {
        /* already logged out on the server */
      }
    }
    tokenStore.clear();
    clearAllDrafts(); // unsaved forms must not stay behind for the next person
    // The next person starts on the dashboard, not on the last screen used.
    navigate('/', { replace: true });
    setMe(null);
    setLogoutReason(reason ? i18n.t(reason === 'idle' ? 'login.loggedOutIdle' : 'login.sessionExpired') : null);
  }, [navigate]);

  useEffect(() => {
    setSessionExpiredHandler(() => {
      setMe(null);
      setLogoutReason(i18n.t('login.sessionExpired'));
    });
  }, []);

  const completeLogin = useCallback(
    async (access: string, refresh: string) => {
      tokenStore.setTokens(access, refresh);
      setLogoutReason(null);
      setLoading(true);
      await loadMe();
    },
    [loadMe],
  );

  const switchBranch = useCallback((id: string) => {
    tokenStore.setBranch(id);
    setBranchId(id);
  }, []);

  const branch = useMemo(() => me?.branches.find((b) => b.id === branchId) ?? null, [me, branchId]);
  const can = useCallback((code: string) => !!branch?.permissions.includes(code), [branch]);

  const value: AuthValue = {
    me, loading, branch, features, hasFeature, reloadFeatures, can, completeLogin, switchBranch, logout, logoutReason,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}
