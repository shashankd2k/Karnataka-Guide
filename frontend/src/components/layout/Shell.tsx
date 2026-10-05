import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';
import { MobileNav } from './MobileNav';
import { useTouristStore } from '../../stores/touristStore';

export const Shell: React.FC = () => {
  const { theme } = useTouristStore();

  // Apply dark theme class to <html>
  useEffect(() => {
    const root = document.documentElement;
    const isDark =
      theme === 'dark' ||
      (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [theme]);

  return (
    <div className="min-h-screen flex flex-col bg-ivory dark:bg-night-slate text-deep-brown dark:text-ivory selection:bg-temple-gold selection:text-deep-brown transition-colors">
      <Header />
      <main className="flex-1 flex flex-col pb-16 md:pb-0">
        <Outlet />
      </main>
      <Footer />
      <MobileNav />
    </div>
  );
};
