import { jsx as _jsx } from "react/jsx-runtime";
// A dropdown whose values come from a master list (e.g. category="blood_group").
import { Select } from 'antd';
import { useMasterLabel, useMasters } from '../api/masters';
export function MasterSelect({ category, ...rest }) {
    const values = useMasters(category);
    const label = useMasterLabel();
    return (_jsx(Select, { allowClear: true, showSearch: true, optionFilterProp: "label", options: values.map((v) => ({ value: v.id, label: label(v) })), ...rest }));
}
