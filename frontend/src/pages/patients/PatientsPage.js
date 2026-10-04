import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
// Patient list with search (by name, mobile number or patient ID). Phone numbers are masked.
import { AlertOutlined, CrownOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { Button, Input, Segmented, Space, Table, Tag, Tooltip, Typography } from 'antd';
import dayjs from 'dayjs';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useMasterLabel } from '../../api/masters';
import { useList } from '../../api/useList';
import { useAuth } from '../../auth/AuthContext';
import { PatientPhoto } from '../../components/PatientPhoto';
export function genderAge(t, gender, age) {
    const g = t(`patients.genderShort.${gender}`);
    return age === null ? g : `${age} ${t('patients.yearsShort')} · ${g}`;
}
export default function PatientsPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { can } = useAuth();
    const masterLabel = useMasterLabel();
    const [search, setSearch] = useState('');
    const [gender, setGender] = useState('all');
    const { rows, loading, pagination, total } = useList('/patients/', {
        q: search || undefined,
        gender: gender === 'all' ? undefined : gender,
    });
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "page-toolbar", children: [_jsxs("div", { children: [_jsx(Typography.Title, { level: 3, style: { margin: 0 }, children: t('patients.title') }), _jsx(Typography.Text, { type: "secondary", children: t('patients.count', { n: total }) })] }), can('patients.create') && (_jsx(Button, { type: "primary", size: "large", icon: _jsx(PlusOutlined, {}), onClick: () => navigate('/patients/new'), children: t('patients.register') }))] }), _jsxs("div", { style: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }, children: [_jsx(Input.Search, { size: "large", allowClear: true, prefix: _jsx(SearchOutlined, { style: { opacity: 0.45 } }), placeholder: t('patients.searchPlaceholder'), onSearch: (value) => setSearch(value.trim()), style: { maxWidth: 520, flex: 1 }, enterButton: t('common.search') }), _jsx(Segmented, { size: "large", value: gender, onChange: (v) => setGender(String(v)), options: [
                            { value: 'all', label: t('patients.all') },
                            { value: 'male', label: t('patients.gender.male') },
                            { value: 'female', label: t('patients.gender.female') },
                        ] })] }), _jsx(Table, { rowKey: "id", loading: loading, dataSource: rows, pagination: pagination, scroll: { x: true }, onRow: (record) => ({ onClick: () => navigate(`/patients/${record.id}`), style: { cursor: 'pointer' } }), locale: { emptyText: search ? t('patients.noResults') : t('patients.empty') }, columns: [
                    {
                        title: t('patients.patient'),
                        key: 'name',
                        render: (_, p) => (_jsxs("div", { style: { display: 'flex', alignItems: 'center', gap: 12 }, children: [_jsx(PatientPhoto, { patientId: p.id, hasPhoto: p.has_photo, name: p.full_name, size: 42 }), _jsxs("div", { children: [_jsxs("div", { style: { fontWeight: 600 }, children: [p.title ? `${masterLabel(p.title)} ` : '', p.full_name] }), _jsx(Typography.Text, { type: "secondary", style: { fontSize: 12, fontFamily: 'monospace' }, children: p.uhid })] })] })),
                    },
                    { title: t('patients.ageGender'), key: 'age', render: (_, p) => genderAge(t, p.gender, p.age_years) },
                    { title: t('patients.mobile'), dataIndex: 'mobile_masked', render: (m) => _jsx("span", { style: { fontFamily: 'monospace' }, children: m }) },
                    { title: t('patients.city'), dataIndex: 'city' },
                    {
                        title: t('patients.registered'), dataIndex: 'registration_date',
                        render: (d, p) => (_jsxs("div", { children: [_jsx("div", { children: dayjs(d).format('DD-MM-YYYY') }), _jsx(Typography.Text, { type: "secondary", style: { fontSize: 12 }, children: p.registered_branch_name })] })),
                    },
                    {
                        title: '', key: 'flags',
                        render: (_, p) => (_jsxs(Space, { size: 4, children: [p.allergy_count > 0 && (_jsx(Tooltip, { title: t('patients.hasAllergies'), children: _jsx(Tag, { color: "red", icon: _jsx(AlertOutlined, {}), children: t('patients.allergyShort') }) })), p.is_vip && _jsx(Tag, { color: "gold", icon: _jsx(CrownOutlined, {}), children: "VIP" }), p.is_foc && _jsx(Tag, { color: "blue", children: "FOC" })] })),
                    },
                ] })] }));
}
