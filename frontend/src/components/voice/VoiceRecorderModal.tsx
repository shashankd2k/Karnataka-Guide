import React from 'react';
import { Mic, Square, X, AlertCircle } from 'lucide-react';
import { AudioWaveform } from './AudioWaveform';
import { useTouristStore } from '../../stores/touristStore';

interface VoiceRecorderModalProps {
  isOpen: boolean;
  durationSeconds: number;
  waveformBars: number[];
  recordingError: string | null;
  onStop: () => void;
  onCancel: () => void;
}

export const VoiceRecorderModal: React.FC<VoiceRecorderModalProps> = ({
  isOpen,
  durationSeconds,
  waveformBars,
  recordingError,
  onStop,
  onCancel,
}) => {
  const { language } = useTouristStore();

  if (!isOpen) return null;

  const minutes = Math.floor(durationSeconds / 60);
  const seconds = durationSeconds % 60;
  const timeFormatted = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-deep-brown/60 dark:bg-black/80 backdrop-blur-sm animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="voice-modal-title"
    >
      <div className="w-full max-w-sm rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/40 shadow-2xl p-6 flex flex-col items-center text-center space-y-5">
        {/* Header */}
        <div className="w-full flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-crimson-rubric opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-crimson-rubric"></span>
            </span>
            <h3 id="voice-modal-title" className="font-display font-bold text-sm text-deep-brown dark:text-ivory">
              {language === 'kn' ? 'ಧ್ವನಿ ರೆಕಾರ್ಡಿಂಗ್' : 'Voice Recording'}
            </h3>
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 rounded-md text-soapstone-grey dark:text-ivory/60 hover:bg-temple-gold/20"
            aria-label="Cancel recording"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Pulsing Mic Icon */}
        <div className="relative flex items-center justify-center">
          <div className="absolute w-24 h-24 rounded-full bg-temple-gold/20 animate-pulse"></div>
          <div className="w-16 h-16 rounded-full bg-temple-gold flex items-center justify-center shadow-lg border-2 border-ivory dark:border-night-card">
            <Mic className="w-8 h-8 text-deep-brown" />
          </div>
        </div>

        {/* Timer Display */}
        <div className="space-y-1">
          <div className="font-mono text-2xl font-bold text-deep-brown dark:text-ivory tracking-widest">
            {timeFormatted}
          </div>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70">
            {language === 'kn'
              ? 'ಸ್ಪಷ್ಟವಾಗಿ ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಮಾತನಾಡಿ...'
              : 'Speak clearly in English or Kannada...'}
          </p>
        </div>

        {/* Animated Waveform */}
        <div className="w-full bg-ivory/50 dark:bg-night-slate/50 rounded-xl border border-temple-gold/20 py-1">
          <AudioWaveform bars={waveformBars} isActive={true} />
        </div>

        {/* Error message */}
        {recordingError && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-crimson-rubric/10 border border-crimson-rubric/30 text-crimson-rubric text-xs text-left">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{recordingError}</span>
          </div>
        )}

        {/* Action Controls */}
        <div className="w-full flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 px-4 py-2.5 rounded-xl border border-soapstone-grey/30 dark:border-night-border text-xs font-semibold text-deep-brown dark:text-ivory hover:bg-soapstone-grey/10 transition-colors"
          >
            {language === 'kn' ? 'ರದ್ದುಮಾಡಿ' : 'Cancel'}
          </button>

          <button
            type="button"
            onClick={onStop}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-temple-gold hover:bg-sandstone-gold text-deep-brown font-bold text-xs shadow-md transition-all active:scale-95"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>{language === 'kn' ? 'ಮುಗಿಸಿ & ಕೇಳಿ' : 'Stop & Send'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
