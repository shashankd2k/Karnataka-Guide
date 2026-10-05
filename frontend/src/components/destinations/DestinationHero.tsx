import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Sparkles, Calendar, Landmark } from 'lucide-react';
import { Destination } from '../../types/tourist';
import { useTouristStore } from '../../stores/touristStore';

interface DestinationHeroProps {
  destination: Destination;
}

export const DestinationHero: React.FC<DestinationHeroProps> = ({ destination }) => {
  const navigate = useNavigate();
  const { language } = useTouristStore();

  const handleAskAI = (query: string) => {
    navigate('/guide', { state: { initialPrompt: query } });
  };

  return (
    <div className="space-y-8">
      {/* Visual Banner */}
      <div className="relative h-72 sm:h-96 w-full rounded-3xl overflow-hidden shadow-2xl border border-temple-gold/30 bg-deep-brown">
        <img
          src={destination.imageAsset}
          alt={destination.name}
          className="w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-deep-brown/95 via-deep-brown/40 to-transparent" />

        {/* Content Overlay */}
        <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-3 py-1 rounded-full text-xs font-bold bg-temple-gold text-deep-brown shadow-sm">
              {destination.dynasty}
            </span>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-deep-brown/80 text-ivory border border-temple-gold/30 backdrop-blur-xs">
              {destination.category}
            </span>
          </div>

          <h1 className="font-display font-extrabold text-3xl sm:text-5xl text-ivory tracking-tight">
            {language === 'kn' ? destination.kannadaName : destination.name}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-xs sm:text-sm text-ivory/80 pt-1">
            <div className="flex items-center gap-1.5">
              <MapPin className="w-4 h-4 text-temple-gold" />
              <span>{destination.district} District, Karnataka</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4 text-temple-gold" />
              <span>{destination.century}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Description & Overview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-display font-bold text-xl text-deep-brown dark:text-ivory flex items-center gap-2">
            <Landmark className="w-5 h-5 text-temple-gold" />
            <span>{language === 'kn' ? 'ಐತಿಹಾಸಿಕ ಪರಿಚಯ' : 'Historical Significance'}</span>
          </h2>
          <p className="text-sm sm:text-base text-soapstone-grey dark:text-ivory/80 leading-relaxed font-sans">
            {language === 'kn' ? destination.kannadaDescription : destination.shortDescription}
          </p>

          {/* Tags */}
          <div className="flex flex-wrap gap-2 pt-2">
            {destination.tags.map((tag, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md text-xs font-medium bg-temple-gold/10 text-deep-brown dark:text-ivory border border-temple-gold/20"
              >
                #{tag}
              </span>
            ))}
          </div>
        </div>

        {/* Suggested AI Queries Card */}
        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/30 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-temple-gold" />
            <h3 className="font-display font-bold text-sm text-deep-brown dark:text-ivory">
              {language === 'kn' ? 'AI ಮಾರ್ಗದರ್ಶಿಗೆ ಕೇಳಿ' : 'Ask AI Guide About This Site'}
            </h3>
          </div>

          <div className="space-y-2">
            {destination.suggestedQueries.map((item, idx) => {
              const query = language === 'kn' ? item.kn : item.en;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleAskAI(query)}
                  className="w-full text-left p-3 rounded-xl border border-soapstone-grey/20 dark:border-night-border bg-ivory/50 dark:bg-night-slate hover:border-temple-gold hover:bg-temple-gold/10 text-xs font-medium text-deep-brown dark:text-ivory transition-all shadow-2xs group cursor-pointer"
                >
                  <span className="group-hover:text-temple-gold">{query}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
