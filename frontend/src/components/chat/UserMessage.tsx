import React from 'react';
import { User } from 'lucide-react';

interface UserMessageProps {
  content: string;
  timestamp?: string;
}

export const UserMessage: React.FC<UserMessageProps> = ({ content, timestamp }) => {
  return (
    <div className="flex justify-end items-end gap-2.5 my-4 pl-8">
      <div className="max-w-2xl bg-deep-brown dark:bg-night-card text-ivory px-4 py-3 rounded-2xl rounded-br-xs shadow-sm border border-temple-gold/20 leading-relaxed text-sm">
        <p className="whitespace-pre-wrap break-words">{content}</p>
        {timestamp && (
          <div className="text-[10px] text-ivory/50 text-right mt-1 font-mono">
            {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>
        )}
      </div>

      <div className="w-8 h-8 rounded-full bg-deep-brown dark:bg-night-card border border-temple-gold/40 flex items-center justify-center shrink-0 shadow-xs">
        <User className="w-4 h-4 text-temple-gold" />
      </div>
    </div>
  );
};
