// "Send Order" window of the check-up screen: make a lab test order slip from the tests advised at this check-up.
// Tick the tests, write the lab's name if you like, mark it urgent, then Print: the slip (in the patient's language) can be
// printed or saved as a PDF and given to the patient or sent to the lab. Below: all the patient's tests and their reports.
// SAFE TO EDIT: the words are in src/i18n/*.json under "consultTools". The slip itself: backend/templates/documents/lab_order.html.
import { PrinterOutlined } from '@ant-design/icons';
import { App, Button, Checkbox, Empty, Input, Modal, Select, Space, Table, Tag } from 'antd';
import dayjs from 'dayjs';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../../api/client';
import type { Investigation, LabTest } from '../../../api/types';
import { DocumentModal } from '../../../components/BillPreview';
import { useAuth } from '../../../auth/AuthContext';

const LAB_KEY = 'order-lab-name';

function savedLab(): string {
  try { return localStorage.getItem(LAB_KEY) ?? ''; } catch { return ''; }
}

export function SendOrderModal({ visitId, patientId, patientName, onClose }: {
  visitId: string; patientId: string; patientName: string; onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const canAdvise = can('emr.edit');
  const [mine, setMine] = useState<Investigation[]>([]); // advised at this check-up
  const [history, setHistory] = useState<Investigation[]>([]); // all of the patient's tests
  const [catalog, setCatalog] = useState<LabTest[]>([]);
  const [ticked, setTicked] = useState<string[] | null>(null); // null = tick all advised tests the first time
  const [lab, setLab] = useState(savedLab);
  const [urgent, setUrgent] = useState(false);
  const [adding, setAdding] = useState<string | undefined>();
  const [printing, setPrinting] = useState(false);

  const lang = i18n.language.slice(0, 2);
  const nameOf = (x: { test_name: string; test_name_gu?: string; test_name_hi?: string }) =>
    (lang === 'gu' && x.test_name_gu) || (lang === 'hi' && x.test_name_hi) || x.test_name;

  const load = useCallback(() => {
    api.get<Investigation[]>('/investigations/', { params: { visit: visitId } })
      .then(({ data }) => setMine(data.filter((r) => r.status === 'advised'))).catch(() => setMine([]));
    api.get<Investigation[]>('/investigations/', { params: { patient: patientId } }).then(({ data }) => setHistory(data)).catch(() => setHistory([]));
  }, [visitId, patientId]);
  useEffect(() => {
    load();
    if (canAdvise) api.get<LabTest[]>('/lab-tests/').then(({ data }) => setCatalog(data)).catch(() => setCatalog([]));
  }, [load, canAdvise]);

  const chosen = (ticked ?? mine.map((r) => r.id)).filter((id) => mine.some((r) => r.id === id));

  const addTest = async (testId: string) => {
    setAdding(undefined);
    try {
      const { data } = await api.post<Investigation>('/investigations/', { visit: visitId, test: testId });
      setTicked([...chosen, data.id]);
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const print = () => {
    try { localStorage.setItem(LAB_KEY, lab.trim()); } catch { /* not remembered */ }
    setPrinting(true);
  };

  return (
    <Modal open onCancel={onClose} footer={null} width={980} centered destroyOnHidden
      title={t('consultTools.orderTitle', { name: patientName })}>
      <div className="so-grid">
        <div>
          <div className="so-label">{t('consultTools.orderTests')}</div>
          {canAdvise && (
            <Select showSearch allowClear optionFilterProp="label" style={{ width: '100%', marginBottom: 8 }} value={adding}
              placeholder={t('investigations.pick')} onChange={(v) => v && addTest(v)}
              options={catalog.filter((x) => !mine.some((r) => r.test === x.id))
                .map((x) => ({ value: x.id, label: (lang === 'gu' && x.name_gu) || (lang === 'hi' && x.name_hi) || x.name }))} />
          )}
          {mine.length === 0 ? <Empty description={t('consultTools.orderNone')} /> : (
            <Checkbox.Group className="so-tests" value={chosen} onChange={(v) => setTicked(v as string[])}>
              {mine.map((r) => (
                <Checkbox key={r.id} value={r.id}>{nameOf(r)}{r.note ? <span className="cell-sub"> — {r.note}</span> : null}</Checkbox>
              ))}
            </Checkbox.Group>
          )}
          <div className="so-label" style={{ marginTop: 14 }}>{t('consultTools.orderLab')}</div>
          <Input value={lab} maxLength={100} onChange={(e) => setLab(e.target.value)} placeholder={t('consultTools.orderLabHelp')} />
          <Space style={{ marginTop: 12 }} wrap>
            <Checkbox checked={urgent} onChange={(e) => setUrgent(e.target.checked)}>{t('consultTools.orderUrgent')}</Checkbox>
            <Button type="primary" icon={<PrinterOutlined />} disabled={chosen.length === 0} onClick={print}>{t('consultTools.orderPrint')}</Button>
          </Space>
        </div>
        <div>
          <div className="so-label">{t('consultTools.orderHistory')}</div>
          <Table<Investigation> size="small" rowKey="id" dataSource={history} pagination={{ pageSize: 8, hideOnSinglePage: true }}
            locale={{ emptyText: t('investigations.none') }} scroll={{ x: true }}
            columns={[
              { title: t('consultTools.orderTest'), render: (_, r) => nameOf(r) },
              { title: t('appointments.date'), dataIndex: 'advised_on', render: (d: string) => dayjs(d).format('DD-MM-YYYY'), width: 110 },
              { title: t('common.status'), dataIndex: 'status', width: 150,
                render: (s: string) => <Tag color={s === 'done' ? 'green' : s === 'cancelled' ? 'default' : 'gold'}>{t(`investigations.status.${s}`, { defaultValue: s })}</Tag> },
            ]} />
        </div>
      </div>
      {printing && (
        <DocumentModal kind="lab-order" id={visitId} title={t('consultTools.orderTitle', { name: patientName })}
          extra={{ tests: chosen.join(','), lab: lab.trim(), urgent: urgent ? 1 : 0 }} onClose={() => setPrinting(false)} />
      )}
    </Modal>
  );
}
