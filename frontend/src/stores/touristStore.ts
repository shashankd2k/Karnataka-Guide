import { create } from 'zustand';
import { LanguageCode, PublicCitationItem } from '../types/tourist';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ActiveDrawer = 'citations' | 'sidebar' | 'none';

interface TouristState {
  sessionUuid: string | null;
  language: LanguageCode;
  theme: ThemeMode;
  activeDrawer: ActiveDrawer;
  selectedCitation: PublicCitationItem | null;
  
  setSessionUuid: (uuid: string | null) => void;
  setLanguage: (lang: LanguageCode) => void;
  setTheme: (theme: ThemeMode) => void;
  setActiveDrawer: (drawer: ActiveDrawer) => void;
  setSelectedCitation: (citation: PublicCitationItem | null) => void;
}

const STORAGE_SESSION_KEY = 'karnataka_guide_session_uuid';
const STORAGE_LANG_KEY = 'karnataka_guide_language';
const STORAGE_THEME_KEY = 'karnataka_guide_theme';

function getInitialSession(): string | null {
  try {
    return localStorage.getItem(STORAGE_SESSION_KEY);
  } catch {
    return null;
  }
}

function getInitialLanguage(): LanguageCode {
  try {
    const stored = localStorage.getItem(STORAGE_LANG_KEY);
    return stored === 'kn' ? 'kn' : 'en';
  } catch {
    return 'en';
  }
}

function getInitialTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_THEME_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
  } catch {
    // Ignored
  }
  return 'system';
}

export const useTouristStore = create<TouristState>((set) => ({
  sessionUuid: getInitialSession(),
  language: getInitialLanguage(),
  theme: getInitialTheme(),
  activeDrawer: 'none',
  selectedCitation: null,

  setSessionUuid: (uuid) => {
    try {
      if (uuid) {
        localStorage.setItem(STORAGE_SESSION_KEY, uuid);
      } else {
        localStorage.removeItem(STORAGE_SESSION_KEY);
      }
    } catch {
      // Ignored
    }
    set({ sessionUuid: uuid });
  },

  setLanguage: (lang) => {
    try {
      localStorage.setItem(STORAGE_LANG_KEY, lang);
    } catch {
      // Ignored
    }
    set({ language: lang });
  },

  setTheme: (theme) => {
    try {
      localStorage.setItem(STORAGE_THEME_KEY, theme);
    } catch {
      // Ignored
    }
    set({ theme });
  },

  setActiveDrawer: (drawer) => set({ activeDrawer: drawer }),
  setSelectedCitation: (citation) => set({ selectedCitation: citation }),
}));
