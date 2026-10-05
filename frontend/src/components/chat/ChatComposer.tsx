import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, Square } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

interface ChatComposerProps {
  onSendMessage: (message: string) => void;
  onOpenVoiceModal: () => void;
  isStreaming?: boolean;
  onAbort?: () => void;
  disabled?: boolean;
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSendMessage,
  onOpenVoiceModal,
  isStreaming = false,
  onAbort,
  disabled = false,
}) => {
  const { language } = useTouristStore();
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleSend = () => {
    if (text.trim() && !disabled && !isStreaming) {
      onSendMessage(text);
      setText('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto p-3 sm:p-4 bg-ivory/90 dark:bg-night-card/90 backdrop-blur-md rounded-2xl border border-temple-gold/30 shadow-lg transition-colors">
      <div className="flex items-end gap-2">
        {/* Text Input */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled || isStreaming}
          rows={1}
          placeholder={
            language === 'kn'
              ? 'ಕರ್ನಾಟಕದ ಇತಿಹಾಸ, ದೇವಾಲಯಗಳ ಬಗ್ಗೆ ಕೇಳಿ... (Enter ಒತ್ತಿ)'
              : 'Ask about Belur, Halebidu, Hampi, Badami... (Press Enter)'
          }
          className="flex-1 max-h-36 resize-none bg-transparent py-2.5 px-3 text-sm text-deep-brown dark:text-ivory placeholder:text-soapstone-grey/60 dark:placeholder:text-ivory/40 focus:outline-none font-sans"
        />

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5 pb-1">
          {/* Mic Button */}
          <button
            type="button"
            onClick={onOpenVoiceModal}
            disabled={disabled || isStreaming}
            className="p-2.5 rounded-xl text-deep-brown dark:text-ivory hover:bg-temple-gold/20 disabled:opacity-40 transition-all border border-temple-gold/30 hover:border-temple-gold"
            aria-label="Open voice recording"
            title={language === 'kn' ? 'ಧ್ವನಿ ಮೂಲಕ ಕೇಳಿ' : 'Ask by voice'}
          >
            <Mic className="w-4 h-4 text-temple-gold" />
          </button>

          {/* Send or Stop Button */}
          {isStreaming ? (
            <button
              type="button"
              onClick={onAbort}
              className="p-2.5 rounded-xl bg-crimson-rubric text-ivory hover:opacity-90 shadow-md transition-all active:scale-95"
              aria-label="Stop generating response"
              title={language === 'kn' ? 'ಉತ್ತರ ನಿಲ್ಲಿಸಿ' : 'Stop generating'}
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={!text.trim() || disabled}
              className="p-2.5 rounded-xl bg-temple-gold hover:bg-sandstone-gold text-deep-brown font-bold disabled:opacity-40 shadow-md transition-all active:scale-95 cursor-pointer disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              <Send className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
