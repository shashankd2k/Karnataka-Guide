import React from 'react';
import { BookOpen, FileText, X, BookmarkCheck } from 'lucide-react';
import { useTouristStore } from '../../stores/touristStore';
import { PublicCitationItem } from '../../types/tourist';

interface CitationDrawerProps {
  citations: PublicCitationItem[];
  onClose: () => void;
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({ citations, onClose }) => {
  const { language, selectedCitation } = useTouristStore();

  return (
    <div
      className="fixed inset-y-0 right-0 z-50 w-full sm:w-96 bg-ivory dark:bg-night-card border-l border-temple-gold/30 shadow-2xl flex flex-col transition-all duration-300 animate-in slide-in-from-right"
      role="dialog"
      aria-labelledby="citations-title"
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-temple-gold/20 bg-temple-gold/10">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-temple-gold" />
          <h2 id="citations-title" className="font-display font-bold text-base text-deep-brown dark:text-ivory">
            {language === 'kn' ? 'ಮೂಲ ಆಧಾರಗಳು' : 'Verified Citations'}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1.5 rounded-lg text-soapstone-grey dark:text-ivory/70 hover:bg-temple-gold/20 hover:text-deep-brown dark:hover:text-ivory transition-colors"
          aria-label="Close citations drawer"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Citations List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {citations.length === 0 ? (
          <div className="text-center py-12 text-soapstone-grey dark:text-ivory/60 text-sm">
            {language === 'kn'
              ? 'ಈ ಉತ್ತರಕ್ಕೆ ನಿರ್ದಿಷ್ಟ ಆಧಾರಗಳು ಲಭ್ಯವಿಲ್ಲ.'
              : 'No specific citations available for this response.'}
          </div>
        ) : (
          citations.map((item, idx) => {
            const isSelected = selectedCitation?.citation_label === item.citation_label;

            return (
              <div
                key={`${item.citation_label}-${idx}`}
                className={`p-4 rounded-xl border transition-all ${
                  isSelected
                    ? 'border-temple-gold bg-temple-gold/15 shadow-md ring-1 ring-temple-gold'
                    : 'border-soapstone-grey/20 dark:border-night-border bg-ivory/80 dark:bg-night-slate/60 hover:border-temple-gold/50'
                }`}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded bg-temple-gold text-deep-brown font-mono font-bold text-xs shadow-xs">
                    {item.citation_label}
                  </span>
                  <div className="flex items-center gap-1 text-xs text-malnad-green dark:text-emerald-400 font-medium">
                    <BookmarkCheck className="w-3.5 h-3.5" />
                    <span>{language === 'kn' ? 'ಪರಿಶೀಲಿಸಿದ ಮೂಲ' : 'Grounded Source'}</span>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-deep-brown/90 dark:text-ivory/90">
                  <div className="flex items-center gap-2 font-medium">
                    <FileText className="w-3.5 h-3.5 text-temple-gold shrink-0" />
                    <span className="truncate">{item.source_filename}</span>
                  </div>

                  <div className="flex items-center gap-3 text-soapstone-grey dark:text-ivory/60 text-[11px] pt-1">
                    <span>
                      {language === 'kn' ? 'ಪುಟ:' : 'Page:'} <strong className="text-deep-brown dark:text-ivory">{item.page_number}</strong>
                    </span>
                    {item.section_header && (
                      <>
                        <span>•</span>
                        <span className="truncate">{item.section_header}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-temple-gold/20 bg-ivory/50 dark:bg-night-slate/40 text-[11px] text-soapstone-grey dark:text-ivory/60 leading-relaxed">
        {language === 'kn'
          ? 'ಪ್ರತಿಯೊಂದು ಉತ್ತರದ ವಾಸ್ತವಾಂಶಗಳನ್ನು ಕರ್ನಾಟಕ ಪ್ರವಾಸೋದ್ಯಮದ ಪರಿಶೀಲಿಸಿದ ದಾಖಲೆಗಳಿಂದ ಪಡೆಯಲಾಗಿದೆ.'
          : 'All facts are authoritatively grounded in verified Karnataka heritage documents.'}
      </div>
    </div>
  );
};
