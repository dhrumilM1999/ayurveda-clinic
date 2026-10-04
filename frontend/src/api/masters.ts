// Dropdown values (masters) from the backend, loaded once and remembered.
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api } from './client';
import type { MasterRef, MasterValue } from './types';

const cache = new Map<string, Promise<MasterValue[]>>();

export function loadMasters(category: string): Promise<MasterValue[]> {
  if (!cache.has(category)) {
    const request = api
      .get<MasterValue[]>('/masters/', { params: { category, is_active: true } })
      .then((r) => r.data)
      .catch((error) => {
        cache.delete(category);
        throw error;
      });
    cache.set(category, request);
  }
  return cache.get(category)!;
}

export function useMasters(category: string) {
  const [values, setValues] = useState<MasterValue[]>([]);
  useEffect(() => {
    let alive = true;
    loadMasters(category).then((v) => alive && setValues(v)).catch(() => undefined);
    return () => {
      alive = false;
    };
  }, [category]);
  return values;
}

/** The label of a dropdown value in the current screen language. */
export function useMasterLabel() {
  const { i18n } = useTranslation();
  return (value: MasterRef | null | undefined) => {
    if (!value) return '';
    if (i18n.language === 'gu' && value.label_gu) return value.label_gu;
    if (i18n.language === 'hi' && value.label_hi) return value.label_hi;
    return value.label;
  };
}

/** Pick the text of a 3-language record, e.g. pickLang(purpose, 'title', 'gu'). */
export function pickLang<T extends object>(record: T, field: string, language: string): string {
  const values = record as Record<string, unknown>;
  const localized = values[`${field}_${language}`];
  return (typeof localized === 'string' && localized) || String(values[field] ?? '');
}
