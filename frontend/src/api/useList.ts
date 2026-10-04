// Loads a list from the API (with page numbers) for tables.
import { App } from 'antd';
import { useCallback, useEffect, useState } from 'react';
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
  const paramsKey = JSON.stringify(params);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get<Page<T> | T[]>(url, {
        params: { ...JSON.parse(paramsKey), page, page_size: pageSize },
      });
      if (Array.isArray(data)) {
        setRows(data);
        setTotal(data.length);
      } else {
        setRows(data.results);
        setTotal(data.count);
      }
    } catch (err) {
      message.error(errorMessage(err, t('common.loadFailed')));
    } finally {
      setLoading(false);
    }
  }, [url, paramsKey, page, pageSize, message, t]);

  useEffect(() => {
    reload();
  }, [reload]);

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

  return { rows, total, loading, reload, pagination };
}
