// Online enquiries (front desk): people who asked for an appointment on the clinic website, by phone or at the desk.
// Call or WhatsApp them, write a note, change the status; "Register patient" opens the registration form already filled.
// SAFE TO EDIT: the words are in src/i18n/*.json under "enquiry".
import { CopyOutlined, PhoneOutlined, PlusOutlined, ReloadOutlined, UserAddOutlined, WhatsAppOutlined } from '@ant-design/icons';
import { App, Button, Card, DatePicker, Form, Input, Modal, Select, Space, Table, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { api, errorMessage } from '../../api/client';
import type { Enquiry, Page } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { LiveSearch, useLatestRequest } from '../../components/LiveSearch';

const STATUSES = ['new', 'contacted', 'appointment', 'not_interested', 'closed'] as const;
const COLORS: Record<string, string> = { new: 'red', contacted: 'gold', appointment: 'green', not_interested: 'default', closed: 'default' };

export default function EnquiriesPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const navigate = useNavigate();
  const canManage = can('enquiries.manage');
  const [rows, setRows] = useState<Enquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<string>('open');
  const [search, setSearch] = useState('');
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [edit, setEdit] = useState<Enquiry | null>(null);
  const [adding, setAdding] = useState(false);
  const [form] = Form.useForm();

  const next = useLatestRequest();
  const load = useCallback(async () => {
    const signal = next();
    setLoading(true);
    try {
      const params: Record<string, unknown> = { page, page_size: 25, search: search || undefined };
      if (status !== 'open' && status !== 'all') params.status = status;
      const { data } = await api.get<Page<Enquiry>>('/enquiries/', { params, signal });
      if (signal.aborted) return;
      setRows(status === 'open' ? data.results.filter((r) => ['new', 'contacted'].includes(r.status)) : data.results);
      setTotal(data.count);
      const summary = await api.get<{ by_status: Record<string, number> }>('/enquiries/summary/');
      setCounts(summary.data.by_status);
    } catch (err) {
      if (!signal.aborted) message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [page, status, search, message, t, next]);
  useEffect(() => { load(); }, [load]);

  const change = async (row: Enquiry, patch: Partial<Enquiry>) => {
    try {
      await api.patch(`/enquiries/${row.id}/`, patch);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const openEdit = (row: Enquiry) => {
    setEdit(row);
    form.setFieldsValue({ notes: row.notes, follow_up_on: row.follow_up_on ? dayjs(row.follow_up_on) : undefined, status: row.status });
  };
  const saveEdit = async () => {
    const v = form.getFieldsValue();
    if (!edit) return;
    await change(edit, { notes: v.notes ?? '', status: v.status, follow_up_on: v.follow_up_on ? v.follow_up_on.format('YYYY-MM-DD') : null });
    setEdit(null);
  };
  const addPhoneEnquiry = async (values: Record<string, string>) => {
    try {
      await api.post('/enquiries/', { name: values.name, phone: values.phone, concern: values.concern ?? '', message: values.message ?? '', source: values.source ?? 'phone' });
      setAdding(false);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const link = `${window.location.origin}/enquiry`;
  const snippet = `<iframe src="${link}" width="100%" height="760" style="border:0"></iframe>`;
  const copy = (text: string) => navigator.clipboard?.writeText(text).then(() => message.success(t('enquiry.copied')));
  const wa = (r: Enquiry) => `https://wa.me/91${r.phone}?text=${encodeURIComponent(t('enquiry.waText', { name: r.name }))}`;
  const register = (r: Enquiry) => navigate(`/patients/new?name=${encodeURIComponent(r.name)}&mobile=${r.phone}&enquiry=${r.id}`);

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('enquiry.pageTitle')}</Typography.Title>
          <div className="cell-sub">{t('enquiry.pageSubtitle')}</div>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>{t('appointments.refresh')}</Button>
          {canManage && <Button type="primary" icon={<PlusOutlined />} onClick={() => setAdding(true)}>{t('enquiry.addPhone')}</Button>}
        </Space>
      </div>

      <Card size="small" style={{ marginBottom: 12 }} title={t('enquiry.websiteTitle')}>
        <div className="cell-sub" style={{ marginBottom: 6 }}>{t('enquiry.websiteHelp')}</div>
        <Space wrap>
          <Input readOnly value={link} style={{ width: 320 }} />
          <Button icon={<CopyOutlined />} onClick={() => copy(link)}>{t('enquiry.copyLink')}</Button>
          <Button icon={<CopyOutlined />} onClick={() => copy(snippet)}>{t('enquiry.copyEmbed')}</Button>
          <Button type="link" href={link} target="_blank">{t('enquiry.openForm')}</Button>
        </Space>
      </Card>

      <div className="filter-bar">
        <LiveSearch placeholder={t('enquiry.search')} onSearch={(v) => { setSearch(v); setPage(1); }} loading={loading} width={280} />
        <Space size={4} wrap>
          {['open', ...STATUSES, 'all'].map((s) => (
            <Tag.CheckableTag key={s} checked={status === s} onChange={() => { setStatus(s); setPage(1); }}>
              {t(`enquiry.status.${s}`)}{s !== 'open' && s !== 'all' ? ` ${counts[s] ?? 0}` : s === 'open' ? ` ${(counts.new ?? 0) + (counts.contacted ?? 0)}` : ''}
            </Tag.CheckableTag>
          ))}
        </Space>
      </div>

      <Table<Enquiry> rowKey="id" loading={loading} dataSource={rows} locale={{ emptyText: t('enquiry.empty') }} scroll={{ x: 1000 }}
        pagination={{ current: page, pageSize: 25, total, showSizeChanger: false, onChange: setPage }}
        columns={[
          { title: t('enquiry.col.received'), width: 130, render: (_: unknown, r) => (
            <><div>{dayjs(r.created_at).format('DD-MM-YYYY')}</div><div className="cell-sub">{dayjs(r.created_at).format('h:mm A')} · {t(`enquiry.source.${r.source}`)}</div></>) },
          { title: t('enquiry.col.who'), render: (_: unknown, r) => (
            <><b>{r.name}</b><div className="cell-sub mono">{r.phone}{r.email ? ` · ${r.email}` : ''}</div>
              {r.patient_uhid && <Tag color="green" bordered={false}>{t('enquiry.patientTag', { uhid: r.patient_uhid })}</Tag>}</>) },
          { title: t('enquiry.col.about'), render: (_: unknown, r) => (
            <>{r.concern && <Tag bordered={false}>{r.concern}</Tag>}<div className="cell-sub">{r.message}</div></>) },
          { title: t('enquiry.col.wants'), width: 160, render: (_: unknown, r) => (
            <>{r.preferred_date ? dayjs(r.preferred_date).format('DD-MM-YYYY') : '—'}<div className="cell-sub">{t(`enquiry.time.${r.preferred_time}`)}{r.branch_name ? ` · ${r.branch_name}` : ''}</div></>) },
          { title: t('enquiry.col.status'), width: 170, render: (_: unknown, r) => (
            canManage
              ? <Select size="small" value={r.status} style={{ width: 150 }} onChange={(v) => change(r, { status: v })}
                  options={STATUSES.map((s) => ({ value: s, label: t(`enquiry.status.${s}`) }))} />
              : <Tag color={COLORS[r.status]}>{r.status_label}</Tag>) },
          { title: '', width: 220, render: (_: unknown, r) => (
            <Space size={4}>
              <Button size="small" icon={<PhoneOutlined />} href={`tel:${r.phone}`} aria-label={t('enquiry.call')} />
              <Button size="small" icon={<WhatsAppOutlined />} href={wa(r)} target="_blank" aria-label="WhatsApp" />
              {canManage && !r.patient && <Button size="small" icon={<UserAddOutlined />} onClick={() => register(r)}>{t('enquiry.register')}</Button>}
              {canManage && <Button size="small" onClick={() => openEdit(r)}>{t('enquiry.notes')}</Button>}
            </Space>) },
        ]} />

      <Modal open={!!edit} title={edit ? `${edit.name} · ${edit.phone}` : ''} onCancel={() => setEdit(null)} onOk={saveEdit}
        okText={t('common.save')} cancelText={t('common.cancel')} destroyOnHidden>
        <Form form={form} layout="vertical">
          <Form.Item name="status" label={t('enquiry.col.status')}><Select options={STATUSES.map((s) => ({ value: s, label: t(`enquiry.status.${s}`) }))} /></Form.Item>
          <Form.Item name="follow_up_on" label={t('enquiry.followUpOn')}><DatePicker format="DD-MM-YYYY" style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="notes" label={t('enquiry.notes')}><Input.TextArea rows={4} maxLength={2000} /></Form.Item>
        </Form>
      </Modal>

      <Modal open={adding} title={t('enquiry.addPhone')} footer={null} onCancel={() => setAdding(false)} destroyOnHidden>
        <Form layout="vertical" onFinish={addPhoneEnquiry} initialValues={{ source: 'phone' }}>
          <Form.Item name="name" label={t('enquiry.name')} rules={[{ required: true, message: t('common.required') }]}><Input /></Form.Item>
          <Form.Item name="phone" label={t('enquiry.phone')} rules={[{ required: true, message: t('common.required') }, { pattern: /^[6-9]\d{9}$/, message: t('enquiry.phoneInvalid') }]}><Input maxLength={10} /></Form.Item>
          <Form.Item name="source" label={t('enquiry.col.source')}>
            <Select options={['phone', 'walk_in', 'other'].map((s) => ({ value: s, label: t(`enquiry.source.${s}`) }))} />
          </Form.Item>
          <Form.Item name="concern" label={t('enquiry.concern')}><Input maxLength={200} /></Form.Item>
          <Form.Item name="message" label={t('enquiry.message')}><Input.TextArea rows={3} maxLength={1000} /></Form.Item>
          <Button type="primary" htmlType="submit" block>{t('common.save')}</Button>
        </Form>
      </Modal>
    </>
  );
}
