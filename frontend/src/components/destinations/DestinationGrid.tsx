import React, { useState } from 'react';
import { DestinationCard } from './DestinationCard';
import { Destination } from '../../types/tourist';
import { Search } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

interface DestinationGridProps {
  destinations: Destination[];
}

export const DestinationGrid: React.FC<DestinationGridProps> = ({ destinations }) => {
  const { language } = useTouristStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDynasty, setSelectedDynasty] = useState('ALL');

  const filterTabs = [
    { id: 'ALL', label: language === 'kn' ? 'ಎಲ್ಲಾ ತಾಣಗಳು' : 'All Sites' },
    { id: 'Hoysala', label: language === 'kn' ? 'ಹೊಯ್ಸಳ' : 'Hoysala' },
    { id: 'Chalukya', label: language === 'kn' ? 'ಚಾಲುಕ್ಯ' : 'Chalukya' },
    { id: 'Vijayanagara', label: language === 'kn' ? 'ವಿಜಯನಗರ' : 'Vijayanagara' },
  ];

  const filtered = destinations.filter((dest) => {
    const matchesSearch =
      dest.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dest.kannadaName.includes(searchQuery) ||
      dest.district.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dest.shortDescription.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesDynasty =
      selectedDynasty === 'ALL' || dest.dynasty.toLowerCase().includes(selectedDynasty.toLowerCase());

    return matchesSearch && matchesDynasty;
  });

  return (
    <div className="space-y-6">
      {/* Search & Filter Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {filterTabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSelectedDynasty(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                selectedDynasty === tab.id
                  ? 'bg-temple-gold text-deep-brown shadow-sm'
                  : 'bg-ivory dark:bg-night-card border border-soapstone-grey/20 dark:border-night-border text-soapstone-grey dark:text-ivory/70 hover:border-temple-gold'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-soapstone-grey dark:text-ivory/50 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={language === 'kn' ? 'ತಾಣ ಹುಡುಕಿ...' : 'Search heritage sites...'}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg text-xs bg-ivory dark:bg-night-card border border-soapstone-grey/20 dark:border-night-border text-deep-brown dark:text-ivory placeholder:text-soapstone-grey/50 focus:outline-none focus:border-temple-gold transition-colors"
          />
        </div>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="text-center py-16 text-soapstone-grey dark:text-ivory/60 text-sm">
          {language === 'kn' ? 'ಯಾವುದೇ ತಾಣಗಳು ಕಂಡುಬಂದಿಲ್ಲ.' : 'No destinations match your search criteria.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filtered.map((dest) => (
            <DestinationCard key={dest.slug} destination={dest} />
          ))}
        </div>
      )}
    </div>
  );
};
