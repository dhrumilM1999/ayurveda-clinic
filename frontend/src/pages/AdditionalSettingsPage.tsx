// Additional settings: optional extra features, switched on/off for the whole organization (clinic).
// Only organization admins can change them. The list itself comes from the server
// (backend/apps/organizations/features_catalog.py -> ADDITIONAL_FEATURES); screen text is in src/i18n.
import { Alert, App, Button, Card, List, Space, Switch, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';
import type { AdditionalFeature } from '../api/types';
import { useAuth } from '../auth/AuthContext';

export default function AdditionalSettingsPage() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { me, reloadFeatures } = useAuth();
  const [rows, setRows] = useState<AdditionalFeature[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const canEdit = !!me?.user.is_org_admin;

  const load = useCallback(async () => {
    try {
      setRows((await api.get<AdditionalFeature[]>('/additional-features/')).data);
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    }
  }, [message, t]);

  useEffect(() => {
    load();
  }, [load]);

  const label = (code: string) => t(`additional.features.${code}.label`, { defaultValue: rows.find((r) => r.code === code)?.label ?? code });

  const setSwitches = async (codes: string[], enabled: boolean, key: string) => {
    setBusy(key);
    try {
      let latest = rows;
      for (const code of codes) {
        latest = (await api.patch<AdditionalFeature[]>(`/additional-features/${code}/`, { enabled })).data;
      }
      setRows(latest);
      await reloadFeatures(); // menus and screens follow straight away
      message.success(t('common.saved'));
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setBusy(null);
    }
  };

  const groups = [...new Set(rows.map((r) => r.group))];

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('additional.title')}</Typography.Title>
          <div className="cell-sub">{t('additional.subtitle')}</div>
        </div>
      </div>
      <Alert type="info" showIcon message={t('additional.keptNote')} style={{ marginBottom: 12 }} />
      {!canEdit && <Alert type="warning" showIcon message={t('additional.onlyAdmin')} style={{ marginBottom: 12 }} />}
      {groups.map((group) => {
        const list = rows.filter((r) => r.group === group);
        return (
          <Card key={group} title={t(`additional.groups.${group}`, { defaultValue: group })} style={{ marginBottom: 12 }}
            extra={canEdit && (
              <Space size={8}>
                <Button size="small" loading={busy === `${group}-on`} onClick={() => setSwitches(list.filter((r) => !r.switched_on).map((r) => r.code), true, `${group}-on`)}>
                  {t('additional.allOn')}
                </Button>
                <Button size="small" loading={busy === `${group}-off`} onClick={() => setSwitches(list.filter((r) => r.switched_on).map((r) => r.code), false, `${group}-off`)}>
                  {t('additional.allOff')}
                </Button>
              </Space>
            )}>
            <List
              dataSource={list}
              renderItem={(row) => (
                <List.Item actions={[
                  <Switch key="s" checked={row.switched_on} disabled={!canEdit} loading={busy === row.code}
                    onChange={(v) => setSwitches([row.code], v, row.code)} aria-label={label(row.code)} />,
                ]}>
                  <List.Item.Meta
                    title={(
                      <Space size={8} wrap>
                        <span>{label(row.code)}</span>
                        {row.requires && row.switched_on && !row.enabled && (
                          <Tag color="orange">{t('additional.needs', { name: label(row.requires) })}</Tag>
                        )}
                      </Space>
                    )}
                    description={t(`additional.features.${row.code}.help`, { defaultValue: '' })}
                  />
                </List.Item>
              )}
            />
          </Card>
        );
      })}
    </>
  );
}
