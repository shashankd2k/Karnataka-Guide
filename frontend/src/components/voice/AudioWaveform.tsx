import React from 'react';

interface AudioWaveformProps {
  bars: number[]; // Array of 5 numbers between 0.1 and 1.0
  isActive?: boolean;
}

export const AudioWaveform: React.FC<AudioWaveformProps> = ({ bars, isActive = true }) => {
  return (
    <div className="flex items-center justify-center gap-1.5 h-12 px-4" aria-hidden="true">
      {bars.map((level, idx) => {
        const heightPercent = Math.max(15, Math.min(100, level * 100));

        return (
          <div
            key={idx}
            className="w-1.5 rounded-full bg-temple-gold transition-all duration-75"
            style={{
              height: isActive ? `${heightPercent}%` : '20%',
              opacity: isActive ? 0.9 : 0.4,
            }}
          />
        );
      })}
    </div>
  );
};
