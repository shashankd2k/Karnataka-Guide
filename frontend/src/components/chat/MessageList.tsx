import React, { useEffect, useRef } from 'react';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';
import { StreamingMessage } from './StreamingMessage';
import { EmptyChatState } from './EmptyChatState';
import { SessionHistoryItem, PublicCitationItem } from '../../types/tourist';

interface MessageListProps {
  history: SessionHistoryItem[];
  isStreaming: boolean;
  streamingUserMessage: string | null;
  streamingAnswer: string;
  streamingCitations: PublicCitationItem[];
  playingMessageId: string | null;
  audioState: string;
  onTogglePlayAudio: (messageId: string) => void;
  onAbortStream: () => void;
  onSelectPrompt: (prompt: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  history,
  isStreaming,
  streamingUserMessage,
  streamingAnswer,
  streamingCitations,
  playingMessageId,
  audioState,
  onTogglePlayAudio,
  onAbortStream,
  onSelectPrompt,
}) => {
  const bottomAnchorRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom as new tokens arrive
  useEffect(() => {
    bottomAnchorRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [history, streamingAnswer, streamingUserMessage]);

  const hasMessages = history.length > 0 || isStreaming || streamingUserMessage;

  if (!hasMessages) {
    return <EmptyChatState onSelectPrompt={onSelectPrompt} />;
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-2 sm:px-4 py-4 space-y-4">
      {/* Historical Messages */}
      {history.map((msg) => {
        if (msg.role === 'user') {
          return <UserMessage key={msg.id} content={msg.content} timestamp={msg.created_at} />;
        }
        return (
          <AssistantMessage
            key={msg.id}
            id={msg.id}
            content={msg.content}
            timestamp={msg.created_at}
            isPlayingAudio={playingMessageId === msg.id && audioState === 'playing'}
            isLoadingAudio={playingMessageId === msg.id && audioState === 'loading'}
            onTogglePlayAudio={onTogglePlayAudio}
          />
        );
      })}

      {/* Ephemeral in-flight Streaming Turn */}
      {streamingUserMessage && <UserMessage content={streamingUserMessage} />}

      {isStreaming && (
        <StreamingMessage
          answer={streamingAnswer}
          citations={streamingCitations}
          onAbort={onAbortStream}
        />
      )}

      <div ref={bottomAnchorRef} className="h-4" />
    </div>
  );
};
