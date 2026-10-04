import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Audit log: who did what and when. Read-only.
import { DatePicker, Input, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useList } from '../api/useList';
const ACTIONS = [
    'view', 'create', 'update', 'delete', 'print', 'export', 'share',
    'login', 'login_failed', 'otp_sent', 'otp_failed', 'logout', 'password_change',
];
const ACTION_COLORS = {
    create: 'green', update: 'blue', delete: 'red', login_failed: 'volcano', otp_failed: 'volcano', print: 'purple',
};
export default function AuditLogPage() {
    const { t } = useTranslation();
    const [action, setAction] = useState();
    const [search, setSearch] = useState('');
    const [range, setRange] = useState(null);
    const { rows, loading, pagination } = useList('/audit-logs/', {
        action,
        search,
        date_from: range?.[0]?.format('YYYY-MM-DD'),
        date_to: range?.[1]?.format('YYYY-MM-DD'),
    });
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('audit.title') }), _jsxs(Space, { wrap: true, children: [_jsx(Select, { allowClear: true, placeholder: t('audit.action'), style: { width: 180 }, value: action, onChange: setAction, options: ACTIONS.map((a) => ({ value: a, label: t(`auditActions.${a}`) })) }), _jsx(DatePicker.RangePicker, { value: range, onChange: (v) => setRange(v), format: "DD-MM-YYYY" }), _jsx(Input.Search, { placeholder: t('common.search'), allowClear: true, onSearch: setSearch, style: { width: 200 } })] })] }), _jsx(Typography.Paragraph, { type: "secondary", children: t('audit.help') }), _jsx(Table, { rowKey: "id", size: "small", loading: loading, dataSource: rows, pagination: pagination, scroll: { x: true }, expandable: {
                    rowExpandable: (r) => Object.keys(r.changes ?? {}).length > 0,
                    expandedRowRender: (r) => _jsx("pre", { style: { margin: 0, whiteSpace: 'pre-wrap' }, children: JSON.stringify(r.changes, null, 2) }),
                }, columns: [
                    { title: t('audit.when'), dataIndex: 'created_at', width: 160, render: (v) => dayjs(v).format('DD-MM-YYYY HH:mm:ss') },
                    { title: t('audit.user'), dataIndex: 'username' },
                    { title: t('audit.action'), dataIndex: 'action', render: (a) => _jsx(Tag, { color: ACTION_COLORS[a], children: t(`auditActions.${a}`, { defaultValue: a }) }) },
                    { title: t('audit.what'), dataIndex: 'object_type' },
                    { title: t('audit.record'), dataIndex: 'object_repr' },
                    { title: t('layout.branch'), dataIndex: 'branch_name' },
                    { title: t('audit.ip'), dataIndex: 'ip_address' },
                ] })] }));
}
