import React, { useState } from 'react';
import { Sparkles, Copy, Check, ShieldCheck, AlertCircle } from 'lucide-react';
import { CitationPill } from '../citations/CitationPill';
import { TTSPlayerButton } from '../voice/TTSPlayerButton';
import { PublicCitationItem } from '../../types/tourist';
import { useTouristStore } from '../../stores/touristStore';

interface AssistantMessageProps {
  id: string;
  content: string;
  citations?: PublicCitationItem[];
  timestamp?: string;
  grounded?: boolean;
  isPlayingAudio?: boolean;
  isLoadingAudio?: boolean;
  onTogglePlayAudio?: (messageId: string) => void;
}

const EXACT_FALLBACK_EN = "Information is not available in the knowledge base.";
const EXACT_FALLBACK_KN = "ಈ ಮಾಹಿತಿಯು ಜ್ಞಾನ ಭಂಡಾರದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.";

export const AssistantMessage: React.FC<AssistantMessageProps> = ({
  id,
  content,
  citations = [],
  timestamp,
  grounded = true,
  isPlayingAudio = false,
  isLoadingAudio = false,
  onTogglePlayAudio,
}) => {
  const { language } = useTouristStore();
  const [copied, setCopied] = useState(false);

  const isFallback = !grounded || content === EXACT_FALLBACK_EN || content === EXACT_FALLBACK_KN;

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Helper to render text with clickable citation badges
  const renderFormattedContent = (text: string) => {
    // Split by citation pattern [1], [2], etc.
    const parts = text.split(/(\[\d+\])/g);

    return parts.map((part, index) => {
      if (/^\[\d+\]$/.test(part)) {
        return <CitationPill key={index} label={part} citations={citations} />;
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <div className="flex justify-start items-start gap-2.5 my-4 pr-4 sm:pr-8">
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-temple-gold/20 dark:bg-night-card border border-temple-gold flex items-center justify-center shrink-0 shadow-xs mt-1">
        <Sparkles className="w-4 h-4 text-temple-gold" />
      </div>

      {/* Assistant Response Card */}
      <div
        className={`max-w-3xl rounded-2xl rounded-tl-xs p-4 sm:p-5 shadow-sm border transition-all text-sm leading-relaxed ${
          isFallback
            ? 'bg-amber-500/5 dark:bg-amber-500/10 border-amber-500/30 text-deep-brown dark:text-ivory'
            : 'bg-ivory/90 dark:bg-night-card border-temple-gold/25 text-deep-brown dark:text-ivory'
        }`}
      >
        {/* Top Meta Bar */}
        <div className="flex items-center justify-between gap-2 mb-2.5 pb-2 border-b border-temple-gold/15 text-xs text-soapstone-grey dark:text-ivory/60">
          <div className="flex items-center gap-1.5 font-semibold text-deep-brown dark:text-ivory font-display">
            <span>{language === 'kn' ? 'AI ಪ್ರವಾಸ ಮಾರ್ಗದರ್ಶಿ' : 'AI Tourist Guide'}</span>
            {isFallback ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-700 dark:text-amber-400 font-normal">
                <AlertCircle className="w-3 h-3" />
                <span>{language === 'kn' ? 'ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲ' : 'Ungrounded'}</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-malnad-green/15 text-malnad-green dark:text-emerald-400 font-normal">
                <ShieldCheck className="w-3 h-3" />
                <span>{language === 'kn' ? 'ಪರಿಶೀಲಿತ ಉತ್ತರ' : 'Grounded'}</span>
              </span>
            )}
          </div>

          {timestamp && (
            <div className="text-[10px] font-mono opacity-70">
              {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </div>
          )}
        </div>

        {/* Answer Content */}
        <div className="whitespace-pre-wrap break-words space-y-2 text-deep-brown dark:text-ivory">
          {renderFormattedContent(content)}
        </div>

        {/* Bottom Actions Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 mt-4 pt-2.5 border-t border-temple-gold/15">
          <div className="flex items-center gap-2">
            {onTogglePlayAudio && !isFallback && (
              <TTSPlayerButton
                assistantMessageId={id}
                isPlaying={isPlayingAudio}
                isLoading={isLoadingAudio}
                onTogglePlay={onTogglePlayAudio}
              />
            )}

            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs text-soapstone-grey dark:text-ivory/70 hover:text-deep-brown dark:hover:text-ivory hover:bg-temple-gold/10 transition-colors"
              aria-label="Copy answer to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-malnad-green" />
                  <span className="text-malnad-green font-medium">{language === 'kn' ? 'ನಕಲಿಸಲಾಗಿದೆ' : 'Copied'}</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>{language === 'kn' ? 'ನಕಲಿಸಿ' : 'Copy'}</span>
                </>
              )}
            </button>
          </div>

          {citations.length > 0 && (
            <div className="text-xs text-soapstone-grey dark:text-ivory/60 flex items-center gap-1">
              <span>{citations.length} {language === 'kn' ? 'ಮೂಲ ಆಧಾರಗಳು' : 'source citations'}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
