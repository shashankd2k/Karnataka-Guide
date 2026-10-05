import React from 'react';
import { HeritageMap } from '../components/map/HeritageMap';
import { useTouristStore } from '../stores/touristStore';
import { MapPin } from 'lucide-react';

export const MapPage: React.FC = () => {
  const { language } = useTouristStore();

  return (
    <div className="flex-1 flex flex-col p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-4">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-temple-gold/15 text-temple-gold border border-temple-gold/30 text-xs font-semibold">
          <MapPin className="w-3.5 h-3.5" />
          <span>{language === 'kn' ? 'ಪರಂಪರೆ ಭೂಪಟ' : 'Karnataka Heritage Map'}</span>
        </div>
        <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-deep-brown dark:text-ivory">
          {language === 'kn' ? 'ಕರ್ನಾಟಕದ ಸ್ಮಾರಕಗಳ ನಕ್ಷೆ' : 'Interactive Monument Map'}
        </h1>
        <p className="text-xs text-soapstone-grey dark:text-ivory/70 font-sans">
          {language === 'kn'
            ? 'ನಕ್ಷೆಯಲ್ಲಿನ ಯಾವುದೇ ಮಾರ್ಕರ್ ಮೇಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ ತಾಣದ ಮಾಹಿತಿ ನೋಡಿ ಮತ್ತು AI ಮಾರ್ಗದರ್ಶಿಯನ್ನು ಕೇಳಿ.'
            : 'Click on any marker to inspect monument details and launch contextual AI queries.'}
        </p>
      </div>

      {/* Map Container */}
      <div className="flex-1 w-full min-h-[500px]">
        <HeritageMap />
      </div>
    </div>
  );
};
