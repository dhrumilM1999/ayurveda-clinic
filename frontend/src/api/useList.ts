// Loads a list from the API (with page numbers) for tables.
import { App } from 'antd';
import { isCancel } from 'axios';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from './client';
import type { Page } from './types';

export function useList<T>(url: string, params: Record<string, unknown> = {}, initialPageSize = 25) {
  const { message } = App.useApp();
  const { t } = useTranslation();
  const [rows, setRows] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [loading, setLoading] = useState(false);
  // true after a failed load: the table must say so instead of looking empty
  const [failed, setFailed] = useState(false);
  const paramsKey = JSON.stringify(params);

  // Only the newest request may update the table (older, slower answers are cancelled and ignored)
  const abort = useRef<AbortController>();

  const reload = useCallback(async () => {
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    setLoading(true);
    try {
      const { data } = await api.get<Page<T> | T[]>(url, {
        params: { ...JSON.parse(paramsKey), page, page_size: pageSize },
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      setFailed(false);
      if (Array.isArray(data)) {
        setRows(data);
        setTotal(data.length);
      } else {
        setRows(data.results);
        setTotal(data.count);
      }
    } catch (err) {
      if (controller.signal.aborted || isCancel(err)) return;
      setFailed(true);
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      if (abort.current === controller) setLoading(false);
    }
  }, [url, paramsKey, page, pageSize, message, t]);

  useEffect(() => {
    reload();
  }, [reload]);
  useEffect(() => () => abort.current?.abort(), []);

  // Go back to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [paramsKey]);

  const pagination = {
    current: page,
    pageSize,
    total,
    showSizeChanger: true,
    onChange: (p: number, size: number) => {
      setPage(p);
      setPageSize(size);
    },
  };

  return { rows, total, loading, failed, reload, pagination };
}
