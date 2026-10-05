import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Compass, MessageSquare, MapPin, Info, Sun, Moon, Monitor, Sparkles } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

export const Header: React.FC = () => {
  const { language, setLanguage, theme, setTheme } = useTouristStore();

  const toggleTheme = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-ivory/85 dark:bg-night-slate/85 border-b border-temple-gold/20 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-temple-gold rounded-lg p-1">
          <div className="w-10 h-10 rounded-lg bg-deep-brown dark:bg-night-card border border-temple-gold/50 flex items-center justify-center shadow-sm group-hover:border-temple-gold transition-colors">
            <svg viewBox="0 0 32 32" className="w-6 h-6 fill-temple-gold">
              <path d="M16 4L19.5 12.5L28 16L19.5 19.5L16 28L12.5 19.5L4 16L12.5 12.5L16 4Z" />
              <circle cx="16" cy="16" r="3" fill="#FDFBF7" />
            </svg>
          </div>
          <div>
            <div className="font-display font-bold text-lg tracking-tight text-deep-brown dark:text-ivory flex items-center gap-1.5">
              <span>Karnataka Guide</span>
              <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded bg-temple-gold/20 text-temple-gold border border-temple-gold/30">AI</span>
            </div>
            <p className="text-xs text-soapstone-grey dark:text-ivory/60 font-sans hidden sm:block">
              {language === 'kn' ? 'ಸ್ಮಾರ್ಟ್ ಪ್ರವಾಸ ಮಾರ್ಗದರ್ಶಿ' : 'Smart Heritage Tourist Guide'}
            </p>
          </div>
        </Link>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-1" aria-label="Main Navigation">
          <NavLink
            to="/guide"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-temple-gold text-deep-brown font-semibold shadow-sm'
                  : 'text-deep-brown/80 dark:text-ivory/80 hover:bg-temple-gold/10 hover:text-deep-brown dark:hover:text-ivory'
              }`
            }
          >
            <MessageSquare className="w-4 h-4" />
            <span>{language === 'kn' ? 'AI ಮಾರ್ಗದರ್ಶಿ' : 'AI Guide'}</span>
          </NavLink>

          <NavLink
            to="/explore"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-temple-gold text-deep-brown font-semibold shadow-sm'
                  : 'text-deep-brown/80 dark:text-ivory/80 hover:bg-temple-gold/10 hover:text-deep-brown dark:hover:text-ivory'
              }`
            }
          >
            <Compass className="w-4 h-4" />
            <span>{language === 'kn' ? 'ತಾಣಗಳು' : 'Explore'}</span>
          </NavLink>

          <NavLink
            to="/map"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-temple-gold text-deep-brown font-semibold shadow-sm'
                  : 'text-deep-brown/80 dark:text-ivory/80 hover:bg-temple-gold/10 hover:text-deep-brown dark:hover:text-ivory'
              }`
            }
          >
            <MapPin className="w-4 h-4" />
            <span>{language === 'kn' ? 'ಭೂಪಟ' : 'Map'}</span>
          </NavLink>

          <NavLink
            to="/about"
            className={({ isActive }) =>
              `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-temple-gold text-deep-brown font-semibold shadow-sm'
                  : 'text-deep-brown/80 dark:text-ivory/80 hover:bg-temple-gold/10 hover:text-deep-brown dark:hover:text-ivory'
              }`
            }
          >
            <Info className="w-4 h-4" />
            <span>{language === 'kn' ? 'ಮಾಹಿತಿ' : 'About'}</span>
          </NavLink>
        </nav>

        {/* Right Controls: Language & Theme */}
        <div className="flex items-center gap-2.5">
          {/* Language Toggle Button */}
          <button
            type="button"
            onClick={() => setLanguage(language === 'en' ? 'kn' : 'en')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-temple-gold/30 hover:border-temple-gold bg-temple-gold/10 text-deep-brown dark:text-ivory text-xs font-semibold tracking-wide transition-colors focus-visible:ring-2 focus-visible:ring-temple-gold"
            aria-label={`Switch language to ${language === 'en' ? 'Kannada' : 'English'}`}
          >
            <Sparkles className="w-3.5 h-3.5 text-temple-gold" />
            <span>{language === 'en' ? 'ಕನ್ನಡ' : 'English'}</span>
          </button>

          {/* Theme Toggle Button */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-lg border border-soapstone-grey/20 dark:border-night-border hover:bg-temple-gold/10 text-soapstone-grey dark:text-ivory/80 transition-colors focus-visible:ring-2 focus-visible:ring-temple-gold"
            aria-label={`Current theme: ${theme}. Click to cycle theme.`}
            title={`Theme: ${theme}`}
          >
            {theme === 'light' && <Sun className="w-4 h-4 text-temple-gold" />}
            {theme === 'dark' && <Moon className="w-4 h-4 text-temple-gold" />}
            {theme === 'system' && <Monitor className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
};
