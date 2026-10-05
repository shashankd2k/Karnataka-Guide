import React from 'react';
import { Sparkles } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

interface SuggestionPillsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const DEFAULT_SUGGESTIONS = {
  en: [
    'Who built the Belur Chennakeshava temple?',
    'Tell me about the Hoysaleswara temple in Halebidu.',
    'What is the stone chariot at Hampi?',
    'Describe the four rock-cut caves of Badami.',
  ],
  kn: [
    'ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ಕಟ್ಟಿಸಿದರು?',
    'ಹಳೇಬೀಡಿನ ಹೊಯ್ಸಳೇಶ್ವರ ದೇವಾಲಯದ ಇತಿಹಾಸವೇನು?',
    'ಹಂಪಿಯ ವಿಜಯ ವಿಠ್ಠಲ ಕಲ್ಲಿನ ರಥದ ಮಹತ್ವವೇನು?',
    'ಬಾದಾಮಿಯ ನಾಲ್ಕು ಗುಹಾ ದೇವಾಲಯಗಳ ವಿವರ ತಿಳಿಸಿ.',
  ],
};

export const SuggestionPills: React.FC<SuggestionPillsProps> = ({ onSelectPrompt, disabled = false }) => {
  const { language } = useTouristStore();
  const suggestions = DEFAULT_SUGGESTIONS[language] || DEFAULT_SUGGESTIONS.en;

  return (
    <div className="flex flex-wrap items-center gap-2 py-2">
      <div className="flex items-center gap-1 text-xs text-soapstone-grey dark:text-ivory/60 mr-1 font-medium">
        <Sparkles className="w-3.5 h-3.5 text-temple-gold" />
        <span>{language === 'kn' ? 'ಸೂಚನೆಗಳು:' : 'Suggestions:'}</span>
      </div>

      {suggestions.map((prompt, idx) => (
        <button
          key={idx}
          type="button"
          disabled={disabled}
          onClick={() => onSelectPrompt(prompt)}
          className="px-3 py-1.5 rounded-full text-xs font-medium bg-ivory dark:bg-night-card border border-temple-gold/30 hover:border-temple-gold text-deep-brown dark:text-ivory hover:bg-temple-gold/10 transition-all text-left shadow-2xs disabled:opacity-50 cursor-pointer"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
};
