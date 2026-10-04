// Shows a patient's photo. Photos are private, so they are loaded through the API (with login).
import { Avatar } from 'antd';
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { clinicConfig } from '../config/clinic';

interface Props {
  patientId: string;
  hasPhoto: boolean;
  name: string;
  size?: number;
  version?: number; // change it to reload after a new photo
}

export function PatientPhoto({ patientId, hasPhoto, name, size = 40, version = 0 }: Props) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!hasPhoto) {
      setUrl(null);
      return;
    }
    let objectUrl: string | null = null;
    api
      .get(`/patients/${patientId}/photo/`, { responseType: 'blob' })
      .then(({ data }) => {
        objectUrl = URL.createObjectURL(data);
        setUrl(objectUrl);
      })
      .catch(() => setUrl(null));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [patientId, hasPhoto, version]);

  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]!.toUpperCase())
    .join('');

  return (
    <Avatar
      size={size}
      src={url ?? undefined}
      style={{ background: url ? undefined : clinicConfig.colors.primary, flex: 'none', fontWeight: 600 }}
    >
      {initials}
    </Avatar>
  );
}
