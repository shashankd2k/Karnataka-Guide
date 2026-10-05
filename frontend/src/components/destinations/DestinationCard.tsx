import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapPin, Sparkles, ArrowRight } from 'lucide-react';
import { Destination } from '../../types/tourist';
import { useTouristStore } from '../../stores/touristStore';

interface DestinationCardProps {
  destination: Destination;
}

export const DestinationCard: React.FC<DestinationCardProps> = ({ destination }) => {
  const navigate = useNavigate();
  const { language } = useTouristStore();

  const handleAskAI = (e: React.MouseEvent) => {
    e.preventDefault();
    const query =
      language === 'kn'
        ? destination.suggestedQueries[0]?.kn || `${destination.kannadaName} ಬಗ್ಗೆ ತಿಳಿಸಿ.`
        : destination.suggestedQueries[0]?.en || `Tell me about ${destination.name}.`;

    navigate('/guide', { state: { initialPrompt: query } });
  };

  return (
    <div className="group flex flex-col rounded-2xl border border-soapstone-grey/20 dark:border-night-border bg-ivory dark:bg-night-card overflow-hidden hover:border-temple-gold/60 hover:shadow-xl transition-all duration-300">
      {/* Image Thumbnail */}
      <Link to={`/explore/${destination.slug}`} className="relative h-48 sm:h-52 w-full overflow-hidden bg-deep-brown">
        <img
          src={destination.imageAsset}
          alt={destination.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-deep-brown/80 via-transparent to-transparent" />

        {/* Dynasty Tag */}
        <span className="absolute top-3 left-3 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-deep-brown/85 text-temple-gold border border-temple-gold/40 backdrop-blur-xs">
          {destination.dynasty}
        </span>
      </Link>

      {/* Card Body */}
      <div className="flex-1 p-5 flex flex-col justify-between space-y-4">
        <div className="space-y-2">
          {/* District Location */}
          <div className="flex items-center gap-1.5 text-xs text-soapstone-grey dark:text-ivory/60">
            <MapPin className="w-3.5 h-3.5 text-temple-gold" />
            <span>{destination.district} District • {destination.century}</span>
          </div>

          {/* Heading */}
          <Link to={`/explore/${destination.slug}`}>
            <h3 className="font-display font-bold text-lg text-deep-brown dark:text-ivory group-hover:text-temple-gold transition-colors">
              {language === 'kn' ? destination.kannadaName : destination.name}
            </h3>
          </Link>

          {/* Short Grounded Description */}
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 line-clamp-3 leading-relaxed font-sans">
            {language === 'kn' ? destination.kannadaDescription : destination.shortDescription}
          </p>
        </div>

        {/* Actions */}
        <div className="pt-3 border-t border-temple-gold/15 flex items-center justify-between gap-2">
          <Link
            to={`/explore/${destination.slug}`}
            className="text-xs font-semibold text-deep-brown dark:text-ivory hover:text-temple-gold flex items-center gap-1"
          >
            <span>{language === 'kn' ? 'ವಿವರಗಳು' : 'Details'}</span>
            <ArrowRight className="w-3 h-3" />
          </Link>

          <button
            type="button"
            onClick={handleAskAI}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-temple-gold text-deep-brown hover:bg-sandstone-gold shadow-xs transition-all active:scale-95 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{language === 'kn' ? 'AI ಕೇಳಿ' : 'Ask AI'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
