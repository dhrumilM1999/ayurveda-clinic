import { jsx as _jsx } from "react/jsx-runtime";
import { Button, Result } from 'antd';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
export default function NotFoundPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    return (_jsx(Result, { status: "404", title: t('common.notFound'), extra: _jsx(Button, { onClick: () => navigate('/'), children: t('menu.dashboard') }) }));
}
