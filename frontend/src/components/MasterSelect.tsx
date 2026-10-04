// A dropdown whose values come from a master list (e.g. category="blood_group").
import { Select, type SelectProps } from 'antd';
import { useMasterLabel, useMasters } from '../api/masters';

interface Props extends Omit<SelectProps, 'options'> {
  category: string;
}

export function MasterSelect({ category, ...rest }: Props) {
  const values = useMasters(category);
  const label = useMasterLabel();
  return (
    <Select
      allowClear
      showSearch
      optionFilterProp="label"
      options={values.map((v) => ({ value: v.id, label: label(v) }))}
      {...rest}
    />
  );
}
