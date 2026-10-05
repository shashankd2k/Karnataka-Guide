import React from 'react';
import { Sparkles, ShieldCheck, Mic, BookOpen } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';

interface EmptyChatStateProps {
  onSelectPrompt: (prompt: string) => void;
}

export const EmptyChatState: React.FC<EmptyChatStateProps> = ({ onSelectPrompt }) => {
  const { language } = useTouristStore();

  const starterCards = [
    {
      title: language === 'kn' ? 'ಬೇಲೂರು ಚೆನ್ನಕೇಶವ' : 'Belur Chennakeshava',
      prompt: language === 'kn' ? 'ಬೇಲೂರು ಚೆನ್ನಕೇಶವ ದೇವಾಲಯವನ್ನು ಯಾರು ನಿರ್ಮಿಸಿದರು?' : 'Who commissioned the Belur Chennakeshava temple and when?',
      desc: language === 'kn' ? 'ಹೊಯ್ಸಳ ಶಿಲ್ಪಕಲೆಯ ಮಹೋನ್ನತ ದೇವಾಲಯ' : 'Hoysala soapstone masterpiece (1117 CE)',
    },
    {
      title: language === 'kn' ? 'ಹಳೇಬೀಡು ಹೊಯ್ಸಳೇಶ್ವರ' : 'Halebidu Hoysaleswara',
      prompt: language === 'kn' ? 'ಹಳೇಬೀಡಿನ ಹೊಯ್ಸಳೇಶ್ವರ ದೇವಾಲಯದ ವಿಶೇಷತೆಗಳೇನು?' : 'Tell me about the twin Hoysaleswara temples in Halebidu.',
      desc: language === 'kn' ? 'ದ್ವಾರಸಮುದ್ರದ ಅದ್ಭುತ ಶಿಲಾ ಕೆತ್ತನೆಗಳು' : 'The ancient capital Dwarasamudra',
    },
    {
      title: language === 'kn' ? 'ಹಂಪಿ ವಿಜಯ ವಿಠ್ಠಲ' : 'Hampi Stone Chariot',
      prompt: language === 'kn' ? 'ಹಂಪಿಯ ಕಲ್ಲಿನ ರಥ ಮತ್ತು ವಿರೂಪಾಕ್ಷ ದೇವಾಲಯದ ಇತಿಹಾಸವೇನು?' : 'What is the history of the Vittala Stone Chariot at Hampi?',
      desc: language === 'kn' ? 'ವಿಜಯನಗರ ಸಾಮ್ರಾಜ್ಯದ ಯುನೆಸ್ಕೋ ತಾಣ' : 'UNESCO World Heritage monument',
    },
    {
      title: language === 'kn' ? 'ಬಾದಾಮಿ ಗುಹೆಗಳು' : 'Badami Rock Caves',
      prompt: language === 'kn' ? 'ಬಾದಾಮಿಯ ನಾಲ್ಕು ಗುಹಾ ದೇವಾಲಯಗಳ ವಿವರಣೆ ನೀಡಿ.' : 'Describe the four rock-cut cave temples of Badami.',
      desc: language === 'kn' ? 'ಚಾಲುಕ್ಯರ ಕೆಂಪು ಮರಳುಗಲ್ಲಿನ ಗುಹೆಗಳು' : 'Chalukya rock-cut cave sanctuaries',
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center text-center py-10 px-4 max-w-2xl mx-auto space-y-6">
      {/* Heritage Emblem */}
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl bg-deep-brown dark:bg-night-card border-2 border-temple-gold flex items-center justify-center shadow-lg">
          <svg viewBox="0 0 32 32" className="w-10 h-10 fill-temple-gold">
            <path d="M16 4L19.5 12.5L28 16L19.5 19.5L16 28L12.5 19.5L4 16L12.5 12.5L16 4Z" />
            <circle cx="16" cy="16" r="3.5" fill="#FDFBF7" />
          </svg>
        </div>
      </div>

      {/* Title & Tagline */}
      <div className="space-y-2">
        <h1 className="font-display font-bold text-2xl sm:text-3xl text-deep-brown dark:text-ivory">
          {language === 'kn' ? 'ಕರ್ನಾಟಕ ಪರಂಪರೆ AI ಮಾರ್ಗದರ್ಶಿ' : 'Karnataka Heritage AI Guide'}
        </h1>
        <p className="text-sm text-soapstone-grey dark:text-ivory/70 max-w-md mx-auto leading-relaxed font-sans">
          {language === 'kn'
            ? 'ಬೇಲೂರು, ಹಳೇಬೀಡು, ಹಂಪಿ, ಬಾದಾಮಿ, ಪಟ್ಟದಕಲ್ಲು ಮತ್ತು ಐಹೊಳೆಯ ಇತಿಹಾಸ, ವಾಸ್ತುಶಿಲ್ಪ ಹಾಗೂ ಪ್ರವಾಸ ಮಾಹಿತಿಯನ್ನು ಕೇಳಿ.'
            : 'Ask factual questions about Karnataka’s historical monuments with instant grounded answers, citations, and audio playback.'}
        </p>
      </div>

      {/* Feature Badges */}
      <div className="flex flex-wrap items-center justify-center gap-3 text-xs text-soapstone-grey dark:text-ivory/80 pt-1">
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-temple-gold/10 border border-temple-gold/25">
          <ShieldCheck className="w-4 h-4 text-malnad-green dark:text-emerald-400" />
          <span>{language === 'kn' ? 'ದಾಖಲೆ ಆಧಾರಿತ' : 'Grounded RAG'}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-temple-gold/10 border border-temple-gold/25">
          <Mic className="w-4 h-4 text-temple-gold" />
          <span>{language === 'kn' ? 'ಧ್ವನಿ ಸಂಭಾಷಣೆ' : 'Voice Assisted'}</span>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-temple-gold/10 border border-temple-gold/25">
          <BookOpen className="w-4 h-4 text-temple-gold" />
          <span>{language === 'kn' ? 'ಪುಟ ಆಧಾರಗಳು' : 'Page Citations'}</span>
        </div>
      </div>

      {/* Starter Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left pt-2">
        {starterCards.map((card, i) => (
          <button
            key={i}
            type="button"
            onClick={() => onSelectPrompt(card.prompt)}
            className="p-4 rounded-xl border border-soapstone-grey/20 dark:border-night-border bg-ivory/80 dark:bg-night-card hover:border-temple-gold hover:bg-temple-gold/10 transition-all text-left group shadow-xs cursor-pointer"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-display font-semibold text-xs text-deep-brown dark:text-ivory group-hover:text-temple-gold">
                {card.title}
              </span>
              <Sparkles className="w-3.5 h-3.5 text-temple-gold opacity-60 group-hover:opacity-100" />
            </div>
            <p className="text-[11px] text-soapstone-grey dark:text-ivory/60 truncate">
              {card.desc}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
};
