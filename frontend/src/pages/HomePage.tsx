import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, MessageSquare, Compass, MapPin, ShieldCheck, Volume2, ArrowRight } from 'lucide-react';
import { DESTINATIONS } from '../data/destinations';
import { useTouristStore } from '../stores/touristStore';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { language } = useTouristStore();

  const handleAskPrompt = (prompt: string) => {
    navigate('/guide', { state: { initialPrompt: prompt } });
  };

  return (
    <div className="flex flex-col space-y-16 py-8 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
      {/* Hero Section */}
      <section className="relative rounded-3xl overflow-hidden bg-gradient-to-b from-deep-brown via-deep-brown/95 to-night-card text-ivory p-8 sm:p-14 lg:p-20 shadow-2xl border border-temple-gold/30">
        <div className="relative z-10 max-w-3xl space-y-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-temple-gold/20 text-temple-gold border border-temple-gold/40 text-xs font-semibold tracking-wide backdrop-blur-xs">
            <Sparkles className="w-4 h-4" />
            <span>
              {language === 'kn' ? 'ಕರ್ನಾಟಕದ ಮೊದಲ ಸ್ಮಾರ್ಟ್ AI ಪ್ರವಾಸ ಮಾರ್ಗದರ್ಶಿ' : 'Smart AI Heritage Tourist Platform'}
            </span>
          </div>

          {/* Main Title */}
          <h1 className="font-display font-extrabold text-3xl sm:text-5xl lg:text-6xl tracking-tight leading-tight">
            {language === 'kn' ? (
              <>ಕರ್ನಾಟಕದ ಭವ್ಯ ಪರಂಪರೆಯನ್ನು <span className="text-temple-gold">AI ಮೂಲಕ</span> ಅನ್ವೇಷಿಸಿ</>
            ) : (
              <>Experience Karnataka’s Timeless Heritage with <span className="text-temple-gold">Grounded AI</span></>
            )}
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-ivory/80 leading-relaxed font-sans max-w-2xl">
            {language === 'kn'
              ? 'ಹೊಯ್ಸಳ, ಚಾಲುಕ್ಯ ಮತ್ತು ವಿಜಯನಗರ ಸಾಮ್ರಾಜ್ಯಗಳ ಅದ್ಭುತ ಶಿಲ್ಪಕಲೆ, ಇತಿಹಾಸ ಮತ್ತು ದೇವಾಲಯಗಳ ಸತ್ಯವಾದ ಮಾಹಿತಿಯನ್ನು ಕನ್ನಡ ಮತ್ತು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಪಡೆಯಿರಿ.'
              : 'Explore Belur, Halebidu, Hampi, Badami, Pattadakal, and Aihole with bilingual voice guidance, verifiable citations, and complete privacy.'}
          </p>

          {/* Primary CTA Buttons */}
          <div className="flex flex-wrap items-center gap-4 pt-4">
            <Link
              to="/guide"
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-temple-gold hover:bg-sandstone-gold text-deep-brown font-bold text-sm sm:text-base shadow-lg transition-all active:scale-95 cursor-pointer"
            >
              <MessageSquare className="w-5 h-5" />
              <span>{language === 'kn' ? 'AI ಮಾರ್ಗದರ್ಶಿಯನ್ನು ಕೇಳಿ' : 'Ask AI Tourist Guide'}</span>
            </Link>

            <Link
              to="/explore"
              className="flex items-center gap-2 px-6 py-3.5 rounded-xl bg-ivory/10 hover:bg-ivory/20 text-ivory border border-temple-gold/40 font-semibold text-sm sm:text-base backdrop-blur-xs transition-all cursor-pointer"
            >
              <Compass className="w-5 h-5 text-temple-gold" />
              <span>{language === 'kn' ? 'ತಾಣಗಳನ್ನು ವೀಕ್ಷಿಸಿ' : 'Explore Heritage Sites'}</span>
            </Link>
          </div>
        </div>

        {/* Decorative Heritage Motif Outline */}
        <div className="absolute right-0 bottom-0 top-0 w-1/3 opacity-10 pointer-events-none hidden lg:flex items-center justify-center">
          <svg viewBox="0 0 100 100" className="w-full h-full stroke-temple-gold fill-none stroke-[0.5]">
            <polygon points="50,5 65,35 95,50 65,65 50,95 35,65 5,50 35,35" />
            <circle cx="50" cy="50" r="25" />
          </svg>
        </div>
      </section>

      {/* Feature Highlights Grid */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 shadow-xs space-y-3">
          <div className="w-12 h-12 rounded-xl bg-temple-gold/15 text-temple-gold flex items-center justify-center border border-temple-gold/30">
            <ShieldCheck className="w-6 h-6 text-malnad-green dark:text-emerald-400" />
          </div>
          <h2 className="font-display font-bold text-lg text-deep-brown dark:text-ivory">
            {language === 'kn' ? 'ಪರಿಶೀಲಿತ & ಸತ್ಯವಾದ ಮಾಹಿತಿ' : 'Authoritative & Grounded'}
          </h2>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed font-sans">
            {language === 'kn'
              ? 'ಪ್ರತಿಯೊಂದು ಉತ್ತರವನ್ನೂ ಅಧಿಕೃತ ದಾಖಲೆಗಳು ಮತ್ತು ಪುಟ ಸಂಖ್ಯೆಯ ಆಧಾರದೊಂದಿಗೆ ನೀಡಲಾಗುತ್ತದೆ. ಯಾವುದೇ ಕಾಲ್ಪನಿಕ ಉತ್ತರವಿಲ್ಲ.'
              : 'Every response is strictly verified against authoritative historical documents with page citations.'}
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 shadow-xs space-y-3">
          <div className="w-12 h-12 rounded-xl bg-temple-gold/15 text-temple-gold flex items-center justify-center border border-temple-gold/30">
            <Volume2 className="w-6 h-6 text-temple-gold" />
          </div>
          <h2 className="font-display font-bold text-lg text-deep-brown dark:text-ivory">
            {language === 'kn' ? 'ದ್ವಿಭಾಷಾ ಧ್ವನಿ ಸಂಭಾಷಣೆ' : 'Bilingual Voice Experience'}
          </h2>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed font-sans">
            {language === 'kn'
              ? 'ಕನ್ನಡ ಮತ್ತು ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಧ್ವನಿಯ ಮೂಲಕ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ ಮತ್ತು ಸ್ವಾಭಾವಿಕ ಧ್ವನಿಯಲ್ಲಿ ಉತ್ತರಗಳನ್ನು ಆಲಿಸಿ.'
              : 'Interact naturally by speaking in Kannada or English, and listen to synthesized audio responses.'}
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-ivory dark:bg-night-card border border-temple-gold/25 shadow-xs space-y-3">
          <div className="w-12 h-12 rounded-xl bg-temple-gold/15 text-temple-gold flex items-center justify-center border border-temple-gold/30">
            <MapPin className="w-6 h-6 text-temple-gold" />
          </div>
          <h2 className="font-display font-bold text-lg text-deep-brown dark:text-ivory">
            {language === 'kn' ? 'ಸಂವಾದಾತ್ಮಕ ಪರಂಪರೆ ಭೂಪಟ' : 'Interactive Heritage Map'}
          </h2>
          <p className="text-xs text-soapstone-grey dark:text-ivory/70 leading-relaxed font-sans">
            {language === 'kn'
              ? 'ಕರ್ನಾಟಕದ ಪ್ರಮುಖ ಸ್ಮಾರಕಗಳನ್ನು ನಕ್ಷೆಯಲ್ಲಿ ಗುರುತಿಸಿ, ಒಂದೇ ಕ್ಲಿಕ್‌ನಲ್ಲಿ AI ಮಾರ್ಗದರ್ಶಿಯ ವಿವರಗಳನ್ನು ಪಡೆಯಿರಿ.'
              : 'Explore monument locations across Karnataka and trigger contextual AI queries with a single tap.'}
          </p>
        </div>
      </section>

      {/* Featured Heritage Destinations */}
      <section className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div className="space-y-1">
            <span className="text-xs font-bold uppercase tracking-widest text-temple-gold">
              {language === 'kn' ? 'ಪ್ರಮುಖ ತಾಣಗಳು' : 'Heritage Highlights'}
            </span>
            <h2 className="font-display font-bold text-2xl sm:text-3xl text-deep-brown dark:text-ivory">
              {language === 'kn' ? 'ಕರ್ನಾಟಕದ ಅದ್ಭುತ ಶಿಲ್ಪಕಲೆ' : 'Featured Architectural Wonders'}
            </h2>
          </div>

          <Link
            to="/explore"
            className="inline-flex items-center gap-1 text-xs sm:text-sm font-semibold text-deep-brown dark:text-ivory hover:text-temple-gold transition-colors"
          >
            <span>{language === 'kn' ? 'ಎಲ್ಲಾ ತಾಣಗಳನ್ನು ವೀಕ್ಷಿಸಿ' : 'View All Destinations'}</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Destination Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {DESTINATIONS.slice(0, 3).map((dest) => (
            <div
              key={dest.slug}
              className="group rounded-2xl border border-soapstone-grey/20 dark:border-night-border bg-ivory dark:bg-night-card overflow-hidden hover:border-temple-gold hover:shadow-xl transition-all flex flex-col justify-between"
            >
              <Link to={`/explore/${dest.slug}`} className="relative h-48 w-full overflow-hidden bg-deep-brown">
                <img
                  src={dest.imageAsset}
                  alt={dest.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  loading="lazy"
                />
                <span className="absolute top-3 left-3 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-deep-brown/85 text-temple-gold border border-temple-gold/40">
                  {dest.dynasty}
                </span>
              </Link>

              <div className="p-5 space-y-3 flex-1 flex flex-col justify-between">
                <div>
                  <h3 className="font-display font-bold text-lg text-deep-brown dark:text-ivory">
                    {language === 'kn' ? dest.kannadaName : dest.name}
                  </h3>
                  <p className="text-xs text-soapstone-grey dark:text-ivory/70 line-clamp-2 leading-relaxed mt-1 font-sans">
                    {language === 'kn' ? dest.kannadaDescription : dest.shortDescription}
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() =>
                    handleAskPrompt(
                      language === 'kn'
                        ? dest.suggestedQueries[0]?.kn || `${dest.kannadaName} ಬಗ್ಗೆ ತಿಳಿಸಿ.`
                        : dest.suggestedQueries[0]?.en || `Tell me about ${dest.name}.`
                    )
                  }
                  className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-temple-gold/15 text-deep-brown dark:text-ivory border border-temple-gold/30 hover:bg-temple-gold hover:text-deep-brown font-semibold text-xs transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-temple-gold group-hover:text-deep-brown" />
                  <span>{language === 'kn' ? 'AI ಕೇಳಿ' : 'Ask AI Guide'}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};
