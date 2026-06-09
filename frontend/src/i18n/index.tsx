import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { Language, Translations } from './types';
import { en, ar } from './translations';

const STORAGE_KEY = 'app-language';

const translationMap: Record<Language, Translations> = { en, ar };

interface I18nContextValue {
  language: Language;
  t: Translations;
  setLanguage: (lang: Language) => void;
  dir: 'ltr' | 'rtl';
}

const I18nContext = createContext<I18nContextValue | null>(null);

function getStoredLanguage(): Language {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'ar' || stored === 'en') return stored;
  } catch {
    // localStorage unavailable
  }
  return 'en';
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(getStoredLanguage);

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // localStorage unavailable
    }
  }, []);

  // Apply dir and lang attributes to <html> element
  useEffect(() => {
    const dir = language === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.dir = dir;
    document.documentElement.lang = language;

    // Add/remove Arabic font class
    if (language === 'ar') {
      document.documentElement.classList.add('lang-ar');
    } else {
      document.documentElement.classList.remove('lang-ar');
    }
  }, [language]);

  const dir = language === 'ar' ? 'rtl' : 'ltr';
  const t = translationMap[language];

  return (
    <I18nContext.Provider value={{ language, t, setLanguage, dir }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
}
