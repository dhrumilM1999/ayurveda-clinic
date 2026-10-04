import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
// Who opened or changed this patient's file (from the audit log).
import { Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from '../../../api/client';
const COLORS = { view: 'default', create: 'green', update: 'blue', delete: 'red', export: 'purple', print: 'purple' };
export function ActivityTab({ patientId }) {
    const { t } = useTranslation();
    const [rows, setRows] = useState([]);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        api.get(`/patients/${patientId}/activity/`)
            .then(({ data }) => setRows(data))
            .finally(() => setLoading(false));
    }, [patientId]);
    return (_jsxs(_Fragment, { children: [_jsx(Typography.Paragraph, { type: "secondary", children: t('patients.activityHelp') }), _jsx(Table, { rowKey: "id", size: "small", loading: loading, dataSource: rows, pagination: { pageSize: 15, hideOnSinglePage: true }, scroll: { x: true }, columns: [
                    { title: t('audit.when'), dataIndex: 'created_at', render: (v) => dayjs(v).format('DD-MM-YYYY HH:mm:ss') },
                    { title: t('audit.user'), dataIndex: 'username' },
                    { title: t('audit.action'), dataIndex: 'action', render: (a) => _jsx(Tag, { color: COLORS[a], children: t(`auditActions.${a}`, { defaultValue: a }) }) },
                    { title: t('audit.what'), dataIndex: 'object_type', render: (v) => t(`patients.objectTypes.${v.replace('.', '_')}`, { defaultValue: v }) },
                    { title: t('layout.branch'), dataIndex: 'branch_name' },
                    { title: t('audit.ip'), dataIndex: 'ip_address' },
                ] })] }));
}
