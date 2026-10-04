import { jsx as _jsx } from "react/jsx-runtime";
// Remembers who is logged in, which branch is chosen, and what they are allowed to do.
// ASK FIRST before editing.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, setSessionExpiredHandler } from '../api/client';
import i18n, { setLanguage } from '../i18n';
import { tokenStore } from './tokenStore';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
    const navigate = useNavigate();
    const [me, setMe] = useState(null);
    const [loading, setLoading] = useState(true);
    const [branchId, setBranchId] = useState(tokenStore.getBranch());
    const [features, setFeatures] = useState({});
    const [logoutReason, setLogoutReason] = useState(null);
    const loadMe = useCallback(async () => {
        if (!tokenStore.getAccess()) {
            setMe(null);
            setLoading(false);
            return;
        }
        try {
            const { data } = await api.get('/auth/me/');
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
        }
        catch {
            tokenStore.clear();
            setMe(null);
        }
        finally {
            setLoading(false);
        }
    }, []);
    useEffect(() => {
        loadMe();
    }, [loadMe]);
    // Load the module on/off switches whenever the branch changes.
    useEffect(() => {
        if (!me || !branchId)
            return;
        api
            .get('/feature-flags/')
            .then(({ data }) => setFeatures(Object.fromEntries(data.map((f) => [f.code, f.enabled]))))
            .catch(() => setFeatures({}));
    }, [me, branchId]);
    const logout = useCallback(async (reason) => {
        const refresh = tokenStore.getRefresh();
        if (refresh) {
            try {
                await api.post('/auth/logout/', { refresh });
            }
            catch {
                /* already logged out on the server */
            }
        }
        tokenStore.clear();
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
    const completeLogin = useCallback(async (access, refresh) => {
        tokenStore.setTokens(access, refresh);
        setLogoutReason(null);
        setLoading(true);
        await loadMe();
    }, [loadMe]);
    const switchBranch = useCallback((id) => {
        tokenStore.setBranch(id);
        setBranchId(id);
    }, []);
    const branch = useMemo(() => me?.branches.find((b) => b.id === branchId) ?? null, [me, branchId]);
    const can = useCallback((code) => !!branch?.permissions.includes(code), [branch]);
    const value = {
        me, loading, branch, features, can, completeLogin, switchBranch, logout, logoutReason,
    };
    return _jsx(AuthContext.Provider, { value: value, children: children });
}
export function useAuth() {
    const value = useContext(AuthContext);
    if (!value)
        throw new Error('useAuth must be used inside <AuthProvider>');
    return value;
}
