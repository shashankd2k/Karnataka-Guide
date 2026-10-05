import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { DESTINATIONS } from '../../data/destinations';
import { useTouristStore } from '../../stores/touristStore';
import { Sparkles, MapPin, WifiOff } from 'lucide-react';

const TILE_URL =
  import.meta.env.VITE_MAP_TILE_URL || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

// Custom Hoysala Kalasha SVG DivIcon
const createKalashaIcon = (name: string) => {
  return L.divIcon({
    className: 'custom-heritage-marker',
    html: `
      <div role="img" aria-label="${name}" style="position: relative; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; cursor: pointer;">
        <svg viewBox="0 0 32 32" width="32" height="32" style="filter: drop-shadow(0 2px 4px rgba(44,24,16,0.5));">
          <path d="M16 2 L20 10 L28 14 L20 18 L16 26 L12 18 L4 14 L12 10 Z" fill="#D4AF37" stroke="#2C1810" stroke-width="1.5"/>
          <circle cx="16" cy="14" r="3.5" fill="#FDFBF7"/>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
    popupAnchor: [0, -18],
  });
};

export const HeritageMap: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useTouristStore();
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const handleAskAI = (prompt: string) => {
    navigate('/guide', { state: { initialPrompt: prompt } });
  };

  // Center on Karnataka: [14.8, 75.8]
  const defaultCenter: [number, number] = [14.85, 75.9];
  const defaultZoom = 7;

  return (
    <div className="relative w-full h-full min-h-[500px] rounded-3xl overflow-hidden border border-temple-gold/30 shadow-xl bg-ivory dark:bg-night-card">
      {/* Offline Status Banner */}
      {!isOnline && (
        <div className="absolute top-4 left-4 right-4 z-[1000] p-3 rounded-xl bg-amber-500/90 text-deep-brown text-xs font-semibold backdrop-blur-md shadow-lg flex items-center gap-2">
          <WifiOff className="w-4 h-4 shrink-0" />
          <span>
            {language === 'kn'
              ? 'ಆನ್‌ಲೈನ್ ಮ್ಯಾಪ್ ಟೈಲ್ಸ್ ಲಭ್ಯವಿಲ್ಲ. ಎಲ್ಲಾ ತಾಣಗಳ ಮಾಹಿತಿ ಹಾಗೂ AI ಮಾರ್ಗದರ್ಶಿ ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ಲಭ್ಯವಿದೆ.'
              : 'Interactive map tiles require an internet connection. All destination details and AI Guide remain available offline.'}
          </span>
        </div>
      )}

      <MapContainer
        center={defaultCenter}
        zoom={defaultZoom}
        scrollWheelZoom={true}
        className="w-full h-full z-10"
        style={{ minHeight: '500px', height: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url={TILE_URL}
        />

        {DESTINATIONS.map((dest) => (
          <Marker
            key={dest.slug}
            position={dest.coordinates}
            icon={createKalashaIcon(dest.name)}
          >
            <Popup className="heritage-map-popup">
              <div className="p-2 space-y-2 max-w-xs text-left">
                <div className="flex items-center gap-1 text-[11px] font-bold text-temple-gold uppercase tracking-wider">
                  <MapPin className="w-3 h-3" />
                  <span>{dest.district} District • {dest.dynasty}</span>
                </div>

                <h4 className="font-display font-bold text-sm text-deep-brown">
                  {language === 'kn' ? dest.kannadaName : dest.name}
                </h4>

                <p className="text-xs text-soapstone-grey line-clamp-2 leading-relaxed">
                  {language === 'kn' ? dest.kannadaDescription : dest.shortDescription}
                </p>

                <div className="pt-2 flex items-center justify-between border-t border-soapstone-grey/20">
                  <button
                    type="button"
                    onClick={() =>
                      handleAskAI(
                        language === 'kn'
                          ? dest.suggestedQueries[0]?.kn || `${dest.kannadaName} ಬಗ್ಗೆ ತಿಳಿಸಿ.`
                          : dest.suggestedQueries[0]?.en || `Tell me about ${dest.name}.`
                      )
                    }
                    className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-temple-gold text-deep-brown font-bold text-xs shadow-xs hover:bg-sandstone-gold transition-colors"
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>{language === 'kn' ? 'AI ಕೇಳಿ' : 'Ask AI'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate(`/explore/${dest.slug}`)}
                    className="text-xs font-semibold text-deep-brown hover:text-temple-gold"
                  >
                    {language === 'kn' ? 'ವಿವರ' : 'Details'} &rarr;
                  </button>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
};
