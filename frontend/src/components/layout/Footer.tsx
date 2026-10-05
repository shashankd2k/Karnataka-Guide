import React from 'react';
import { useTouristStore } from '../../stores/touristStore';

export const Footer: React.FC = () => {
  const { language } = useTouristStore();

  return (
    <footer className="w-full border-t border-temple-gold/15 bg-ivory dark:bg-night-slate/90 py-6 px-4 sm:px-6 lg:px-8 text-xs text-soapstone-grey dark:text-ivory/60 transition-colors">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-center sm:text-left">
          <span className="font-semibold text-deep-brown dark:text-ivory">
            {language === 'kn' ? 'ಕರ್ನಾಟಕ ಸ್ಮಾರ್ಟ್ ಪ್ರವಾಸ ಮಾರ್ಗದರ್ಶಿ' : 'Karnataka Smart Tourist Guide'}
          </span>
          <span>•</span>
          <span>
            {language === 'kn' ? 'ಹೊಯ್ಸಳ ಮತ್ತು ಚಾಲುಕ್ಯ ಪರಂಪರೆ' : 'Hoysala & Chalukya Heritage'}
          </span>
        </div>

        <div className="flex items-center gap-4 text-center sm:text-right">
          <span>
            {language === 'kn' ? '100% ಗೌಪ್ಯತೆ • ಲಾಗಿನ್ ಅಗತ್ಯವಿಲ್ಲ' : '100% Privacy • Anonymous Access'}
          </span>
          <span>•</span>
          <span>
            {language === 'kn' ? 'ಆಧಾರಿತ AI ಉತ್ತರಗಳು' : 'Grounded RAG Intelligence'}
          </span>
        </div>
      </div>
    </footer>
  );
};
