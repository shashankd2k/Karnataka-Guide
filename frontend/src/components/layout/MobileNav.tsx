import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, MessageSquare, Compass, MapPin } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

export const MobileNav: React.FC = () => {
  const { language } = useTouristStore();

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-ivory/95 dark:bg-night-slate/95 backdrop-blur-lg border-t border-temple-gold/20 px-2 py-1.5 flex items-center justify-around"
      aria-label="Mobile Navigation"
    >
      <NavLink
        to="/"
        className={({ isActive }) =>
          `flex flex-col items-center gap-1 p-2 rounded-lg text-xs font-medium transition-colors ${
            isActive
              ? 'text-temple-gold font-bold'
              : 'text-deep-brown/70 dark:text-ivory/70 hover:text-temple-gold'
          }`
        }
      >
        <Home className="w-5 h-5" />
        <span>{language === 'kn' ? 'ಮುಖಪುಟ' : 'Home'}</span>
      </NavLink>

      <NavLink
        to="/guide"
        className={({ isActive }) =>
          `flex flex-col items-center gap-1 p-2 rounded-lg text-xs font-medium transition-colors ${
            isActive
              ? 'text-temple-gold font-bold'
              : 'text-deep-brown/70 dark:text-ivory/70 hover:text-temple-gold'
          }`
        }
      >
        <MessageSquare className="w-5 h-5" />
        <span>{language === 'kn' ? 'ಮಾರ್ಗದರ್ಶಿ' : 'AI Guide'}</span>
      </NavLink>

      <NavLink
        to="/explore"
        className={({ isActive }) =>
          `flex flex-col items-center gap-1 p-2 rounded-lg text-xs font-medium transition-colors ${
            isActive
              ? 'text-temple-gold font-bold'
              : 'text-deep-brown/70 dark:text-ivory/70 hover:text-temple-gold'
          }`
        }
      >
        <Compass className="w-5 h-5" />
        <span>{language === 'kn' ? 'ತಾಣಗಳು' : 'Explore'}</span>
      </NavLink>

      <NavLink
        to="/map"
        className={({ isActive }) =>
          `flex flex-col items-center gap-1 p-2 rounded-lg text-xs font-medium transition-colors ${
            isActive
              ? 'text-temple-gold font-bold'
              : 'text-deep-brown/70 dark:text-ivory/70 hover:text-temple-gold'
          }`
        }
      >
        <MapPin className="w-5 h-5" />
        <span>{language === 'kn' ? 'ಭೂಪಟ' : 'Map'}</span>
      </NavLink>
    </nav>
  );
};
