import React from 'react';
import { ShieldCheck, Sparkles, Mic, BookOpen, Lock, Compass } from 'lucide-react';
import { useTouristStore } from '../stores/touristStore';

export const AboutPage: React.FC = () => {
  const { language } = useTouristStore();

  return (
    <div className="max-w-4xl mx-auto py-10 px-4 sm:px-6 lg:px-8 space-y-10 w-full font-sans">
      {/* Title */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-temple-gold/15 text-temple-gold border border-temple-gold/30 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>{language === 'kn' ? 'ವೇದಿಕೆಯ ಬಗ್ಗೆ' : 'About the Platform'}</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-4xl text-deep-brown dark:text-ivory">
          {language === 'kn'
            ? 'ಕರ್ನಾಟಕದ ಸ್ಮಾರ್ಟ್ AI ಪ್ರವಾಸ ಮಾರ್ಗದರ್ಶಿ'
            : 'AI-Powered Smart Tourist Guide Platform'}
        </h1>
        <p className="text-xs sm:text-sm text-soapstone-grey dark:text-ivory/70 max-w-xl mx-auto leading-relaxed">
          {language === 'kn'
            ? 'ಕರ್ನಾಟಕದ ಐತಿಹಾಸಿಕ ತಾಣಗಳ ಸತ್ಯವಾದ ಜ್ಞಾನವನ್ನು ಭಾಷಾ ತಡೆಗಳಿಲ್ಲದೆ ಪ್ರತಿಯೊಬ್ಬರಿಗೂ ತಲುಪಿಸುವ ನವೀನ ತಂತ್ರಜ್ಞಾನ ವೇದಿಕೆ.'
            : 'A modern state-of-the-art platform delivering grounded, verifiable, and bilingual heritage intelligence for tourists and scholars.'}
        </p>
      </div>

      {/* Core Principles Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-temple-gold font-display font-bold text-sm">
            <ShieldCheck className="w-5 h-5 text-malnad-green dark:text-emerald-400" />
            <span>{language === 'kn' ? 'ಸತ್ಯಾಸತ್ಯತೆ & ಆಧಾರಗಳು' : 'Strict Grounding & Citations'}</span>
          </div>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed">
            {language === 'kn'
              ? 'ಪ್ರತಿಯೊಂದು ಉತ್ತರವನ್ನು ಪರಿಶೀಲಿಸಿದ ಐತಿಹಾಸಿಕ ದಾಖಲೆಗಳಿಂದ ಪಡೆಯಲಾಗುತ್ತದೆ ಮತ್ತು ಪುಟ ಸಂಖ್ಯೆಯೊಂದಿಗೆ ಆಧಾರ ನೀಡಲಾಗುತ್ತದೆ. ಮಾಹಿತಿ ಲಭ್ಯವಿಲ್ಲದಿದ್ದಾಗ ನೇರವಾಗಿ ತಿಳಿಸಲಾಗುತ್ತದೆ.'
              : 'All responses are generated from verified PDF source documents with exact page-level citations. The AI strictly refrains from fabricating facts.'}
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-temple-gold font-display font-bold text-sm">
            <Lock className="w-5 h-5 text-temple-gold" />
            <span>{language === 'kn' ? '100% ಗೌಪ್ಯತೆ' : 'Privacy & Anonymous Access'}</span>
          </div>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed">
            {language === 'kn'
              ? 'ಯಾವುದೇ ಲಾಗಿನ್ ಅಥವಾ ವೈಯಕ್ತಿಕ ವಿವರಗಳ ಅಗತ್ಯವಿಲ್ಲ. ನಿಮ್ಮ ಸಂಭಾಷಣೆಗಳನ್ನು ನೀವು ಯಾವುದೇ ಕ್ಷಣದಲ್ಲಿ ಅಳಿಸಬಹುದು.'
              : 'Zero user authentication required. No personal information is collected, and session history can be cleared instantly.'}
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-temple-gold font-display font-bold text-sm">
            <Mic className="w-5 h-5 text-temple-gold" />
            <span>{language === 'kn' ? 'ದ್ವಿಭಾಷಾ ಧ್ವನಿ ಸಂವಾದ' : 'Offline Multilingual Voice'}</span>
          </div>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed">
            {language === 'kn'
              ? 'ಕನ್ನಡ (Noto Sans Kannada) ಮತ್ತು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಧ್ವನಿಯ ಮೂಲಕ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ, ಸ್ವಾಭಾವಿಕ ಆಡಿಯೋ ಉತ್ತರಗಳನ್ನು ಆಲಿಸಿ.'
              : 'Voice recognition (Faster-Whisper STT) and neural speech synthesis (Piper & MMS-TTS) support fluid English and Kannada.'}
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 space-y-2.5 shadow-xs">
          <div className="flex items-center gap-2 text-temple-gold font-display font-bold text-sm">
            <Compass className="w-5 h-5 text-temple-gold" />
            <span>{language === 'kn' ? 'ಪರಂಪರೆ ತಾಣಗಳ ಜಾಲ' : 'Karnataka Heritage Sites'}</span>
          </div>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed">
            {language === 'kn'
              ? 'ಬೇಲೂರು, ಹಳೇಬೀಡು, ಹಂಪಿ, ಬಾದಾಮಿ, ಪಟ್ಟದಕಲ್ಲು ಮತ್ತು ಐಹೊಳೆಯ ವಾಸ್ತುಶಿಲ್ಪ ಹಾಗೂ ಇತಿಹಾಸವನ್ನು ಅನ್ವೇಷಿಸಿ.'
              : 'Discover Hoysala, Chalukya, and Vijayanagara architectural masterworks across Karnataka.'}
          </p>
        </div>
      </div>

      {/* How to Use Section */}
      <div className="p-6 sm:p-8 rounded-3xl bg-ivory/80 dark:bg-night-card border border-temple-gold/20 space-y-4">
        <h2 className="font-display font-bold text-lg text-deep-brown dark:text-ivory flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-temple-gold" />
          <span>{language === 'kn' ? 'ಬಳಸುವ ವಿಧಾನ' : 'How to Use the Guide'}</span>
        </h2>
        <ul className="space-y-2.5 text-xs sm:text-sm text-soapstone-grey dark:text-ivory/70 list-disc list-inside leading-relaxed">
          <li>{language === 'kn' ? 'ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಮೈಕ್ರೋಫೋನ್ ಬಟನ್ ಒತ್ತಿ ಮಾತನಾಡಿ.' : 'Type your question or click the microphone icon to speak in English or Kannada.'}</li>
          <li>{language === 'kn' ? 'ಉತ್ತರದಲ್ಲಿರುವ [1], [2] ಆಧಾರಗಳ ಮೇಲೆ ಕ್ಲಿಕ್ ಮಾಡಿ ಮೂಲ ದಾಖಲೆ ಮತ್ತು ಪುಟ ಸಂಖ್ಯೆಯನ್ನು ವೀಕ್ಷಿಸಿ.' : 'Click on citation badges like [1] to inspect the source PDF filename and page number.'}</li>
          <li>{language === 'kn' ? 'ಉತ್ತರ ಮುಗಿದ ನಂತರ "ಆಲಿಸಿ" ಬಟನ್ ಒತ್ತಿ ಧ್ವನಿ ವಿವರಣೆಯನ್ನು ಕೇಳಿ.' : 'Click "Listen" on any completed answer to hear natural speech synthesis.'}</li>
          <li>{language === 'kn' ? 'ತಾಣಗಳ ಪಟ್ಟಿ ಮತ್ತು ನಕ್ಷೆಯ ಮೂಲಕ ಸುಲಭವಾಗಿ ಸಂಚರಿಸಿ.' : 'Browse the Explore catalog or Interactive Map to discover new destinations.'}</li>
        </ul>
      </div>
    </div>
  );
};
