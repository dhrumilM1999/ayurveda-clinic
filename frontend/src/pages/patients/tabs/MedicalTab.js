import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { LockOutlined } from '@ant-design/icons';
import { Alert, Col, Empty, Row, Table, Tag, Typography } from 'antd';
import { useTranslation } from 'react-i18next';
import { useMasterLabel } from '../../../api/masters';
const SEVERITY_COLOR = { mild: 'green', moderate: 'orange', severe: 'red' };
export function MedicalTab({ patient: p }) {
    const { t } = useTranslation();
    const label = useMasterLabel();
    return (_jsxs(Row, { gutter: [24, 24], children: [_jsxs(Col, { span: 24, children: [_jsx(Typography.Title, { level: 5, children: t('patients.fields.conditions') }), p.medical_history_hidden ? (_jsx(Alert, { type: "info", showIcon: true, icon: _jsx(LockOutlined, {}), message: t('patients.historyHidden') })) : p.conditions && p.conditions.length > 0 ? (_jsx("div", { style: { display: 'flex', flexWrap: 'wrap', gap: 8 }, children: p.conditions.map((c) => (_jsxs(Tag, { color: "purple", style: { padding: '4px 10px', fontSize: 13 }, children: [label(c.condition), c.since ? ` · ${c.since}` : ''] }, c.id))) })) : (_jsx(Typography.Text, { type: "secondary", children: t('patients.noneRecorded') }))] }), _jsxs(Col, { xs: 24, lg: 12, children: [_jsx(Typography.Title, { level: 5, children: t('patients.fields.allergies') }), _jsx(Table, { rowKey: "id", size: "small", pagination: false, dataSource: p.allergies, locale: { emptyText: _jsx(Empty, { image: Empty.PRESENTED_IMAGE_SIMPLE, description: t('patients.noAllergies') }) }, columns: [
                            { title: t('patients.allergen'), dataIndex: 'allergen' },
                            { title: t('patients.allergyType'), dataIndex: 'allergy_type', render: (v) => label(v) },
                            { title: t('patients.severityLabel'), dataIndex: 'severity', render: (s) => _jsx(Tag, { color: SEVERITY_COLOR[s], children: t(`patients.severity.${s}`) }) },
                            { title: t('patients.reaction'), dataIndex: 'reaction' },
                        ] })] }), _jsxs(Col, { xs: 24, lg: 12, children: [_jsx(Typography.Title, { level: 5, children: t('patients.fields.medications') }), _jsx(Table, { rowKey: "id", size: "small", pagination: false, dataSource: p.medications, locale: { emptyText: _jsx(Empty, { image: Empty.PRESENTED_IMAGE_SIMPLE, description: t('patients.noneRecorded') }) }, columns: [
                            { title: t('patients.medicineName'), dataIndex: 'name' },
                            { title: t('patients.dose'), dataIndex: 'dose' },
                            { title: t('patients.frequency'), dataIndex: 'frequency' },
                            { title: t('patients.since'), dataIndex: 'since' },
                        ] })] }), !p.medical_history_hidden && (_jsx(Col, { span: 24, children: _jsx(Row, { gutter: [16, 16], children: ['past_history', 'family_history', 'surgical_history', 'other_notes'].map((f) => (_jsx(Col, { xs: 24, md: 12, children: _jsxs("div", { className: "history-box", children: [_jsx("div", { className: "history-label", children: t(`patients.fields.${f}`) }), _jsx("div", { className: "history-text", children: p[f] || _jsx(Typography.Text, { type: "secondary", children: "\u2014" }) })] }) }, f))) }) }))] }));
}
