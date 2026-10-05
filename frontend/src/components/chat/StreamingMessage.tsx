import React from 'react';
import { Sparkles, StopCircle, Loader2 } from 'lucide-react';
import { CitationPill } from '../citations/CitationPill';
import { PublicCitationItem } from '../../types/tourist';
import { useTouristStore } from '../../stores/touristStore';

interface StreamingMessageProps {
  answer: string;
  citations?: PublicCitationItem[];
  onAbort?: () => void;
}

export const StreamingMessage: React.FC<StreamingMessageProps> = ({
  answer,
  citations = [],
  onAbort,
}) => {
  const { language } = useTouristStore();

  const renderFormattedContent = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, index) => {
      if (/^\[\d+\]$/.test(part)) {
        return <CitationPill key={index} label={part} citations={citations} />;
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="flex justify-start items-start gap-2.5 my-4 pr-4 sm:pr-8 animate-in fade-in">
      <div className="w-8 h-8 rounded-full bg-temple-gold/20 dark:bg-night-card border border-temple-gold flex items-center justify-center shrink-0 shadow-xs mt-1 animate-pulse">
        <Sparkles className="w-4 h-4 text-temple-gold" />
      </div>

      <div className="max-w-3xl flex-1 rounded-2xl rounded-tl-xs p-4 sm:p-5 shadow-sm border border-temple-gold/40 bg-ivory/95 dark:bg-night-card text-deep-brown dark:text-ivory text-sm leading-relaxed">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-2.5 pb-2 border-b border-temple-gold/15 text-xs">
          <div className="flex items-center gap-2 text-temple-gold font-semibold font-display">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            <span>{language === 'kn' ? 'ಉತ್ತರವನ್ನು ರಚಿಸಲಾಗುತ್ತಿದೆ...' : 'Generating response...'}</span>
          </div>

          {onAbort && (
            <button
              type="button"
              onClick={onAbort}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold text-crimson-rubric bg-crimson-rubric/10 hover:bg-crimson-rubric/20 transition-colors"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>{language === 'kn' ? 'ನಿಲ್ಲಿಸಿ' : 'Stop'}</span>
            </button>
          )}
        </div>

        {/* Streaming Content */}
        <div className="whitespace-pre-wrap break-words">
          {answer ? (
            <>
              {renderFormattedContent(answer)}
              <span className="inline-block w-2 h-4 ml-1 bg-temple-gold animate-pulse align-middle" />
            </>
          ) : (
            <span className="text-soapstone-grey dark:text-ivory/50 italic">
              {language === 'kn' ? 'ಜ್ಞಾನ ಭಂಡಾರದಿಂದ ಮಾಹಿತಿಯನ್ನು ಸಂಗ್ರಹಿಸಲಾಗುತ್ತಿದೆ...' : 'Gathering grounded knowledge...'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
