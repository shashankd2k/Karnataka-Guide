import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { DESTINATIONS } from '../data/destinations';
import { DestinationHero } from '../components/destinations/DestinationHero';
import { ArrowLeft } from 'lucide-react';
import { useTouristStore } from '../stores/touristStore';

export const DestinationDetailPage: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const { language } = useTouristStore();

  const destination = DESTINATIONS.find((d) => d.slug === slug);

  if (!destination) {
    return (
      <div className="max-w-4xl mx-auto py-20 px-4 text-center space-y-4">
        <h2 className="font-display font-bold text-2xl text-deep-brown dark:text-ivory">
          {language === 'kn' ? 'ತಾಣ ಕಂಡುಬಂದಿಲ್ಲ' : 'Destination Not Found'}
        </h2>
        <p className="text-xs text-soapstone-grey dark:text-ivory/60">
          {language === 'kn'
            ? 'ನೀವು ಹುಡುಕುತ್ತಿರುವ ತಾಣವು ನಮ್ಮ ಪಟ್ಟಿಯಲ್ಲಿಲ್ಲ.'
            : 'The requested destination does not exist in our catalog.'}
        </p>
        <Link
          to="/explore"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-temple-gold text-deep-brown font-semibold text-xs"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>{language === 'kn' ? 'ತಾಣಗಳ ಪಟ್ಟಿಗೆ ಹಿಂತಿರುಗಿ' : 'Back to Destinations'}</span>
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6 w-full">
      {/* Back Link */}
      <Link
        to="/explore"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-soapstone-grey dark:text-ivory/70 hover:text-temple-gold transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>{language === 'kn' ? 'ಎಲ್ಲಾ ತಾಣಗಳಿಗೆ ಹಿಂತಿರುಗಿ' : 'Back to all destinations'}</span>
      </Link>

      <DestinationHero destination={destination} />
    </div>
  );
};
