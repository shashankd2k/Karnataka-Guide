import React from 'react';
import { DestinationGrid } from '../components/destinations/DestinationGrid';
import { DESTINATIONS } from '../data/destinations';
import { useTouristStore } from '../stores/touristStore';
import { Compass } from 'lucide-react';

export const ExplorePage: React.FC = () => {
  const { language } = useTouristStore();

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8 w-full">
      {/* Header */}
      <div className="space-y-2 max-w-2xl">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-temple-gold/15 text-temple-gold border border-temple-gold/30 text-xs font-semibold">
          <Compass className="w-3.5 h-3.5" />
          <span>{language === 'kn' ? 'ಕರ್ನಾಟಕ ಪರಂಪರೆ ತಾಣಗಳು' : 'Heritage Destination Catalog'}</span>
        </div>
        <h1 className="font-display font-extrabold text-2xl sm:text-4xl text-deep-brown dark:text-ivory">
          {language === 'kn' ? 'ಐತಿಹಾಸಿಕ ತಾಣಗಳ ಅನ್ವೇಷಣೆ' : 'Explore Karnataka Heritage'}
        </h1>
        <p className="text-xs sm:text-sm text-soapstone-grey dark:text-ivory/70 leading-relaxed font-sans">
          {language === 'kn'
            ? 'ಕರ್ನಾಟಕದ ಪ್ರಮುಖ ಐತಿಹಾಸಿಕ ತಾಣಗಳ ಪಟ್ಟಿ. ಯಾವುದೇ ತಾಣದ ಬಗ್ಗೆ ನೇರವಾಗಿ AI ಮಾರ್ಗದರ್ಶಿಯನ್ನು ಕೇಳಬಹುದು.'
            : 'Verified historical destinations across Hoysala, Chalukya, and Vijayanagara dynasties.'}
        </p>
      </div>

      {/* Grid */}
      <DestinationGrid destinations={DESTINATIONS} />
    </div>
  );
};
