// "Translate" button for forms that have English + Gujarati + Hindi boxes: fills Gujarati and Hindi from the English
// text using the free local AI (Ollama). It only SUGGESTS: the user can edit the boxes before saving.
// If the AI is not running it says "AI is offline" and typing by hand still works.
// SAFE TO EDIT: nothing here; the words are in src/i18n/*.json under "translate".
import { TranslationOutlined } from '@ant-design/icons';
import { App, Button, Popconfirm, Tooltip } from 'antd';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../api/client';

export interface Translated { gu: string; hi: string }

export function TranslateButton({ english, existing, onResult, iconOnly = false, size = 'small' }: {
  english: string;
  /** what is already in the Gujarati / Hindi boxes (asks before replacing) */
  existing: { gu?: string; hi?: string };
  onResult: (result: Translated) => void;
  iconOnly?: boolean;
  size?: 'small' | 'middle';
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [busy, setBusy] = useState(false);
  const filled = !!(existing.gu?.trim() || existing.hi?.trim());

  const run = async () => {
    if (!english.trim()) {
      message.warning(t('translate.writeEnglish'));
      return;
    }
    setBusy(true);
    try {
      const { data } = await api.post<Translated>('/translate/', { text: english.trim(), targets: ['gu', 'hi'] });
      onResult({ gu: data.gu ?? '', hi: data.hi ?? '' });
      message.success(t('translate.done'));
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      message.error(status === 503 ? t('translate.offline') : errorMessage(err, t('translate.failed')));
    } finally {
      setBusy(false);
    }
  };

  const button = (
    <Tooltip title={t('translate.hint')}>
      <Button size={size} icon={<TranslationOutlined />} loading={busy} onClick={filled ? undefined : run}>
        {iconOnly ? null : t('translate.button')}
      </Button>
    </Tooltip>
  );
  return filled
    ? <Popconfirm title={t('translate.replaceAsk')} okText={t('common.yes')} cancelText={t('common.no')} onConfirm={run}>{button}</Popconfirm>
    : button;
}
