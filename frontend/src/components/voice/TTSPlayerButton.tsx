import React from 'react';
import { Volume2, Pause, Loader2 } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

interface TTSPlayerButtonProps {
  assistantMessageId: string;
  isPlaying: boolean;
  isLoading: boolean;
  onTogglePlay: (messageId: string) => void;
}

export const TTSPlayerButton: React.FC<TTSPlayerButtonProps> = ({
  assistantMessageId,
  isPlaying,
  isLoading,
  onTogglePlay,
}) => {
  const { language } = useTouristStore();

  return (
    <button
      type="button"
      onClick={() => onTogglePlay(assistantMessageId)}
      disabled={isLoading}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold tracking-wide transition-all border ${
        isPlaying
          ? 'bg-temple-gold text-deep-brown border-temple-gold shadow-sm ring-1 ring-temple-gold'
          : 'bg-ivory dark:bg-night-card border-temple-gold/30 hover:border-temple-gold text-deep-brown dark:text-ivory hover:bg-temple-gold/10'
      } disabled:opacity-60 cursor-pointer`}
      aria-label={
        isPlaying
          ? (language === 'kn' ? 'ಆಡಿಯೋ ನಿಲ್ಲಿಸಿ' : 'Pause speech')
          : (language === 'kn' ? 'ಉತ್ತರವನ್ನು ಆಲಿಸಿ' : 'Listen to response')
      }
    >
      {isLoading ? (
        <>
          <Loader2 className="w-3.5 h-3.5 animate-spin text-temple-gold" />
          <span>{language === 'kn' ? 'ಸಿದ್ಧಪಡಿಸಲಾಗುತ್ತಿದೆ...' : 'Synthesizing...'}</span>
        </>
      ) : isPlaying ? (
        <>
          <Pause className="w-3.5 h-3.5 fill-current" />
          <span>{language === 'kn' ? 'ನಿಲ್ಲಿಸಿ' : 'Pause'}</span>
        </>
      ) : (
        <>
          <Volume2 className="w-3.5 h-3.5 text-temple-gold" />
          <span>{language === 'kn' ? 'ಆಲಿಸಿ' : 'Listen'}</span>
        </>
      )}
    </button>
  );
};
