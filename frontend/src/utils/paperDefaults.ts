// The paper each document opens with in the print window (chosen in Settings -> PDF settings).
// Loaded once and remembered; forgotten after the PDF settings are saved (call resetPaperDefaults).
import { useEffect, useState } from 'react';
import { api } from '../api/client';

type PaperMap = Record<string, string>;
let cache: Promise<PaperMap> | null = null;

export function resetPaperDefaults() {
  cache = null;
}

function load(): Promise<PaperMap> {
  if (!cache) {
    // If the server cannot be reached, every document simply opens with its usual paper.
    cache = api.get<PaperMap>('/print-settings/paper-defaults/').then((r) => r.data).catch(() => ({}));
  }
  return cache;
}

/** {document type: paper}, or null while loading. */
export function usePaperDefaults(): PaperMap | null {
  const [map, setMap] = useState<PaperMap | null>(null);
  useEffect(() => {
    let alive = true;
    load().then((m) => alive && setMap(m));
    return () => { alive = false; };
  }, []);
  return map;
}

/** The paper to open first: the saved one when this print window offers it, else `fallback`. */
export function startPaper(map: PaperMap, docType: string, offered: string[], fallback: string): string {
  const wanted = map[docType];
  return wanted && offered.includes(wanted) ? wanted : fallback;
}
