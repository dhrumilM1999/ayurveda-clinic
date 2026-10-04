// Sets up the three screen languages. The words themselves are in en.json, gu.json, hi.json.
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { clinicConfig } from '../config/clinic';
import en from './en.json';
import gu from './gu.json';
import hi from './hi.json';

export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'gu', label: 'ગુજરાતી' },
  { code: 'hi', label: 'हिन्दी' },
];

const saved = localStorage.getItem('language');

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, gu: { translation: gu }, hi: { translation: hi } },
  lng: saved || clinicConfig.defaultLanguage,
  // If a Gujarati or Hindi word is missing, show the English one.
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export function setLanguage(code: string) {
  i18n.changeLanguage(code);
  localStorage.setItem('language', code);
  document.documentElement.lang = code;
}

document.documentElement.lang = i18n.language;

export default i18n;
