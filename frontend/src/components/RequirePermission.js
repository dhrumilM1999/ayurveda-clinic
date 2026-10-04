import { jsx as _jsx, Fragment as _Fragment } from "react/jsx-runtime";
// Shows the screen only if the user has the permission in the current branch.
import { Result } from 'antd';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
export function RequirePermission({ code, children }) {
    const { can } = useAuth();
    const { t } = useTranslation();
    if (!can(code)) {
        return _jsx(Result, { status: "403", title: t('common.noAccessTitle'), subTitle: t('common.noAccessText') });
    }
    return _jsx(_Fragment, { children: children });
}
