import React from 'react';
import { Trash2, Sparkles, MapPin, X } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';
import { DESTINATIONS } from '../../data/destinations';

interface SidebarProps {
  onSelectPrompt: (prompt: string) => void;
  onClearHistory: () => Promise<void>;
  isClearing?: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onSelectPrompt,
  onClearHistory,
  isClearing = false,
  onClose,
}) => {
  const { language, sessionUuid } = useTouristStore();

  return (
    <aside className="h-full flex flex-col justify-between p-4 bg-ivory/60 dark:bg-night-card border-r border-temple-gold/20 overflow-y-auto">
      <div className="space-y-6">
        {/* Header / Mobile Close */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-deep-brown dark:text-ivory font-display font-semibold text-sm">
            <Sparkles className="w-4 h-4 text-temple-gold" />
            <span>{language === 'kn' ? 'ತ್ವರಿತ ಪ್ರಶ್ನೆಗಳು' : 'Heritage Prompts'}</span>
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="md:hidden p-1.5 rounded-md hover:bg-temple-gold/10 text-soapstone-grey dark:text-ivory"
              aria-label="Close sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Destination Quick Prompts */}
        <div className="space-y-2">
          <p className="text-xs uppercase font-bold tracking-wider text-soapstone-grey dark:text-ivory/50">
            {language === 'kn' ? 'ತಾಣಗಳ ಬಗ್ಗೆ ಕೇಳಿ' : 'Explore Sites'}
          </p>
          <div className="flex flex-col gap-1.5">
            {DESTINATIONS.map((dest) => {
              const query = language === 'kn'
                ? dest.suggestedQueries[0]?.kn || `${dest.kannadaName} ಬಗ್ಗೆ ತಿಳಿಸಿ.`
                : dest.suggestedQueries[0]?.en || `Tell me about ${dest.name}.`;

              return (
                <button
                  key={dest.slug}
                  type="button"
                  onClick={() => {
                    onSelectPrompt(query);
                    if (onClose) onClose();
                  }}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs font-medium text-deep-brown dark:text-ivory hover:bg-temple-gold/15 transition-colors border border-transparent hover:border-temple-gold/30 group"
                >
                  <MapPin className="w-3.5 h-3.5 text-temple-gold shrink-0 group-hover:scale-110 transition-transform" />
                  <span className="truncate">
                    {language === 'kn' ? dest.kannadaName : dest.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer / Session Controls */}
      <div className="pt-4 border-t border-temple-gold/15 space-y-3">
        {sessionUuid && (
          <div className="text-[11px] text-soapstone-grey dark:text-ivory/50 truncate font-mono">
            {language === 'kn' ? 'ಅಧಿವೇಶನ:' : 'Session:'} {sessionUuid.slice(0, 8)}...
          </div>
        )}

        <button
          type="button"
          onClick={onClearHistory}
          disabled={isClearing}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-crimson-rubric bg-crimson-rubric/10 hover:bg-crimson-rubric/20 transition-colors disabled:opacity-50"
        >
          <Trash2 className="w-3.5 h-3.5" />
          <span>
            {isClearing
              ? (language === 'kn' ? 'ಅಳಿಸಲಾಗುತ್ತಿದೆ...' : 'Clearing...')
              : (language === 'kn' ? 'ಸಂಭಾಷಣೆ ಅಳಿಸಿ' : 'Clear Conversation')}
          </span>
        </button>
      </div>
    </aside>
  );
};
