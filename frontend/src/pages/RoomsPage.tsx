// Rooms of the current branch, plus the room-type dropdown list.
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { Room, RoomType } from '../api/types';
import { useList } from '../api/useList';
import { useAuth } from '../auth/AuthContext';

export default function RoomsPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { can, branch } = useAuth();
  const { rows, loading, reload, pagination } = useList<Room>('/rooms/');
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([]);
  const [editing, setEditing] = useState<Partial<Room> | null>(null);
  const [typesOpen, setTypesOpen] = useState(false);
  const [newType, setNewType] = useState('');
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const canManage = can('rooms.manage');

  const loadTypes = useCallback(async () => {
    const { data } = await api.get<RoomType[]>('/room-types/');
    setRoomTypes(data);
  }, []);

  useEffect(() => {
    loadTypes().catch(() => undefined);
  }, [loadTypes]);

  const open = (room?: Room) => {
    setEditing(room ?? {});
    form.setFieldsValue(room ?? { capacity: 1, is_active: true });
  };

  const save = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      if (editing?.id) await api.patch(`/rooms/${editing.id}/`, values);
      else await api.post('/rooms/', values);
      message.success(t('common.saved'));
      setEditing(null);
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (room: Room) => {
    try {
      await api.delete(`/rooms/${room.id}/`);
      message.success(t('common.removed'));
      reload();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const addType = async () => {
    if (!newType.trim()) return;
    try {
      await api.post('/room-types/', { name: newType.trim(), sort_order: roomTypes.length });
      setNewType('');
      loadTypes();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    }
  };

  const toggleType = async (type: RoomType) => {
    await api.patch(`/room-types/${type.id}/`, { is_active: !type.is_active });
    loadTypes();
  };

  return (
    <>
      <div className="page-toolbar">
        <Typography.Title level={3} style={{ margin: 0 }}>{t('rooms.title', { branch: branch?.name })}</Typography.Title>
        {canManage && (
          <Space>
            <Button onClick={() => setTypesOpen(true)}>{t('rooms.manageTypes')}</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => open()}>{t('rooms.add')}</Button>
          </Space>
        )}
      </div>
      <Table<Room>
        rowKey="id"
        loading={loading}
        dataSource={rows}
        pagination={pagination}
        scroll={{ x: true }}
        columns={[
          { title: t('rooms.name'), dataIndex: 'name' },
          { title: t('rooms.type'), dataIndex: 'room_type_name' },
          { title: t('rooms.capacity'), dataIndex: 'capacity', width: 100 },
          { title: t('rooms.notes'), dataIndex: 'notes' },
          {
            title: t('common.status'), dataIndex: 'is_active',
            render: (active: boolean) => active ? <Tag color="green">{t('common.active')}</Tag> : <Tag>{t('common.inactive')}</Tag>,
          },
          ...(canManage ? [{
            title: '', key: 'actions', width: 160,
            render: (_: unknown, room: Room) => (
              <Space>
                <Button size="small" onClick={() => open(room)}>{t('common.edit')}</Button>
                <Popconfirm title={t('rooms.confirmRemove')} onConfirm={() => remove(room)} okText={t('common.yes')} cancelText={t('common.no')}>
                  <Button size="small" danger icon={<DeleteOutlined />} aria-label={t('common.remove')} />
                </Popconfirm>
              </Space>
            ),
          }] : []),
        ]}
      />

      <Modal
        open={!!editing}
        title={editing?.id ? t('rooms.edit') : t('rooms.add')}
        onCancel={() => setEditing(null)}
        onOk={save}
        confirmLoading={saving}
        okText={t('common.save')}
        cancelText={t('common.cancel')}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label={t('rooms.name')} rules={[{ required: true, message: t('common.required') }]}>
            <Input />
          </Form.Item>
          <Form.Item name="room_type" label={t('rooms.type')}>
            <Select allowClear options={roomTypes.filter((rt) => rt.is_active).map((rt) => ({ value: rt.id, label: rt.name }))} />
          </Form.Item>
          <Form.Item name="capacity" label={t('rooms.capacity')}><InputNumber min={1} max={100} /></Form.Item>
          <Form.Item name="notes" label={t('rooms.notes')}><Input /></Form.Item>
          <Form.Item name="is_active" label={t('common.active')} valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>

      <Modal open={typesOpen} title={t('rooms.manageTypes')} onCancel={() => setTypesOpen(false)} footer={null}>
        <Space.Compact style={{ width: '100%', marginBottom: 12 }}>
          <Input value={newType} onChange={(e) => setNewType(e.target.value)} placeholder={t('rooms.newType')} onPressEnter={addType} />
          <Button type="primary" onClick={addType}>{t('common.add')}</Button>
        </Space.Compact>
        <Table<RoomType>
          rowKey="id"
          size="small"
          pagination={false}
          dataSource={roomTypes}
          columns={[
            { title: t('rooms.type'), dataIndex: 'name' },
            {
              title: t('common.active'), dataIndex: 'is_active', width: 90,
              render: (_: boolean, rt: RoomType) => <Switch size="small" checked={rt.is_active} onChange={() => toggleType(rt)} />,
            },
          ]}
        />
      </Modal>
    </>
  );
}
