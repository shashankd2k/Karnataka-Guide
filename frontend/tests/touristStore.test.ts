import { describe, it, expect, beforeEach } from 'vitest';
import { useTouristStore } from '../src/stores/touristStore';

describe('Tourist Store (Zustand)', () => {
  beforeEach(() => {
    localStorage.clear();
    useTouristStore.setState({
      sessionUuid: null,
      language: 'en',
      theme: 'system',
      activeDrawer: 'none',
      selectedCitation: null,
    });
  });

  it('updates and persists sessionUuid', () => {
    useTouristStore.getState().setSessionUuid('12345-67890');
    expect(useTouristStore.getState().sessionUuid).toBe('12345-67890');
    expect(localStorage.getItem('karnataka_guide_session_uuid')).toBe('12345-67890');
  });

  it('toggles language and synchronizes with localStorage', () => {
    useTouristStore.getState().setLanguage('kn');
    expect(useTouristStore.getState().language).toBe('kn');
    expect(localStorage.getItem('karnataka_guide_language')).toBe('kn');

    useTouristStore.getState().setLanguage('en');
    expect(useTouristStore.getState().language).toBe('en');
    expect(localStorage.getItem('karnataka_guide_language')).toBe('en');
  });

  it('sets theme mode and updates localStorage', () => {
    useTouristStore.getState().setTheme('dark');
    expect(useTouristStore.getState().theme).toBe('dark');
    expect(localStorage.getItem('karnataka_guide_theme')).toBe('dark');
  });

  it('manages drawer open/close states', () => {
    useTouristStore.getState().setActiveDrawer('citations');
    expect(useTouristStore.getState().activeDrawer).toBe('citations');

    useTouristStore.getState().setActiveDrawer('sidebar');
    expect(useTouristStore.getState().activeDrawer).toBe('sidebar');

    useTouristStore.getState().setActiveDrawer('none');
    expect(useTouristStore.getState().activeDrawer).toBe('none');
  });
});
