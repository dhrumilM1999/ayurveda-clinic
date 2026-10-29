// The clinic's list of therapies (Abhyanga, Shirodhara, Virechana ...): name in 3 languages, stage, time, usual oil, price.
// SAFE TO EDIT: the words are in src/i18n/*.json under "therapy". The starting list is backend/apps/therapy/catalog.py.
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, InputNumber, Modal, Select, Space, Switch, Table, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { Page, TherapyType } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { STAGES, StageTag, useTherapyName } from './common';
import { TranslateButton } from '../../components/TranslateButton';

interface Service { id: string; name: string; price: string }

export default function TherapiesTab({ rows, reload }: { rows: TherapyType[]; reload: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can, hasFeature } = useAuth();
  const canManage = can('therapy.manage');
  const name = useTherapyName();
  const [editing, setEditing] = useState<Partial<TherapyType> | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (!editing || !hasFeature('opd_billing') || !can('billing.view')) return;
    api.get<Page<Service> | Service[]>('/services/', { params: { page_size: 200 } })
      .then(({ data }) => setServices(Array.isArray(data) ? data : data.results)).catch(() => undefined);
  }, [editing, hasFeature, can]);

  const open = (row?: TherapyType) => {
    setEditing(row ?? {});
    form.resetFields();
    form.setFieldsValue(row ?? { stage: 'pradhana', duration_minutes: 45, is_active: true });
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing?.id) await api.patch(`/therapies/${editing.id}/`, values);
      else await api.post('/therapies/', values);
      message.success(t('common.saved'));
      setEditing(null);
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const loadSample = async () => {
    try {
      const { data } = await api.post<{ added: number }>('/therapies/load-sample/');
      message.success(t('therapy.list.loadedN', { n: data.added }));
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  return (
    <>
      {canManage && (
        <Space style={{ marginBottom: 12 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('therapy.list.add')}</Button>
          <Button onClick={loadSample}>{t('therapy.list.loadSample')}</Button>
        </Space>
      )}
      <Table<TherapyType>
        rowKey="id" size="small" dataSource={rows} pagination={false} scroll={{ x: 'max-content' }}
        locale={{ emptyText: t('therapy.list.empty') }}
        onRow={(r) => (canManage ? { onClick: () => open(r), style: { cursor: 'pointer' } } : {})}
        columns={[
          { title: t('therapy.list.name'), render: (_, r) => <div><Typography.Text strong>{name(r)}</Typography.Text>
            {name(r) !== r.name && <div className="cell-sub">{r.name}</div>}</div> },
          { title: t('therapy.list.stage'), render: (_, r) => <StageTag stage={r.stage} /> },
          { title: t('therapy.list.minutes'), dataIndex: 'duration_minutes', width: 90 },
          { title: t('therapy.list.material'), dataIndex: 'default_material' },
          { title: t('therapy.list.service'), render: (_, r) => (r.price ? `₹${r.price}` : <span className="cell-sub">{t('therapy.list.noService')}</span>) },
          { title: t('therapy.list.active'), width: 90, render: (_, r) => (r.is_active ? t('common.yes') : t('common.no')) },
        ]}
      />
      <Modal open={!!editing} title={editing?.id ? t('therapy.list.edit') : t('therapy.list.add')} onCancel={() => setEditing(null)} onOk={save}
        confirmLoading={saving} okText={t('common.save')} width={640} destroyOnHidden>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('therapy.list.name')} rules={[{ required: true, message: t('common.required') }]}><Input maxLength={150} /></Form.Item>
          <Form.Item noStyle shouldUpdate>{() => (
  <TranslateButton english={form.getFieldValue('name') ?? ''} existing={{ gu: form.getFieldValue('name_gu'), hi: form.getFieldValue('name_hi') }}
    onResult={(r) => form.setFieldsValue({ name_gu: r.gu, name_hi: r.hi })} />
)}</Form.Item>
          <Space style={{ width: '100%', marginTop: 8 }} styles={{ item: { flex: 1 } }} align="start">
            <Form.Item name="name_gu" label={t('therapy.list.nameGu')}><Input maxLength={150} /></Form.Item>
            <Form.Item name="name_hi" label={t('therapy.list.nameHi')}><Input maxLength={150} /></Form.Item>
          </Space>
          <Space wrap align="start">
            <Form.Item name="stage" label={t('therapy.list.stage')}>
              <Select style={{ width: 260 }} options={STAGES.map((s) => ({ value: s, label: t(`therapy.stage.${s}`) }))} />
            </Form.Item>
            <Form.Item name="duration_minutes" label={t('therapy.list.minutes')}><InputNumber min={5} max={600} step={5} /></Form.Item>
            <Form.Item name="is_active" label={t('therapy.list.active')} valuePropName="checked"><Switch /></Form.Item>
          </Space>
          <Form.Item name="default_material" label={t('therapy.list.material')}><Input maxLength={150} /></Form.Item>
          {services.length > 0 && (
            <Form.Item name="service" label={t('therapy.list.service')}>
              <Select allowClear showSearch optionFilterProp="label"
                options={services.map((s) => ({ value: s.id, label: `${s.name} (₹${s.price})` }))} />
            </Form.Item>
          )}
          {hasFeature('opd_billing') && !editing?.service && (
            <Form.Item name="set_price" label={t('therapy.list.setPrice')} extra={t('therapy.list.setPriceHelp')}>
              <InputNumber min={0} max={1000000} prefix="₹" style={{ width: 160 }} />
            </Form.Item>
          )}
          <Form.Item name="instructions" label={t('therapy.list.instructions')}><Input.TextArea rows={3} maxLength={1500} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
}
