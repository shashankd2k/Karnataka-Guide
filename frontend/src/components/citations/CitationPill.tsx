import React from 'react';
import { PublicCitationItem } from '../../types/tourist';
import { useTouristStore } from '../../stores/touristStore';

interface CitationPillProps {
  label: string;
  citations?: PublicCitationItem[];
}

export const CitationPill: React.FC<CitationPillProps> = ({ label, citations = [] }) => {
  const { setSelectedCitation, setActiveDrawer } = useTouristStore();

  const matchingCitation = citations.find((c) => c.citation_label === label);

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (matchingCitation) {
      setSelectedCitation(matchingCitation);
      setActiveDrawer('citations');
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      title={
        matchingCitation
          ? `Source: ${matchingCitation.source_filename}, Page ${matchingCitation.page_number}`
          : `Citation ${label}`
      }
      className="inline-flex items-center justify-center px-1.5 py-0.2 mx-0.5 text-[11px] font-bold font-mono rounded bg-temple-gold/15 hover:bg-temple-gold text-deep-brown dark:text-temple-gold dark:hover:text-deep-brown border border-temple-gold/40 hover:border-temple-gold transition-all cursor-pointer select-none align-baseline shadow-xs"
      aria-label={`View citation ${label}`}
    >
      {label}
    </button>
  );
};
