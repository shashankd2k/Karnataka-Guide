import { useState, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { streamChatTurn } from '../services/sseClient';
import { sendVoiceChatTurn, ApiError } from '../services/apiClient';
import { useTouristStore } from '../stores/touristStore';
import { PublicCitationItem, SessionHistoryItem } from '../types/tourist';

export type VoiceProcessingStage = 'idle' | 'recording' | 'transcribing' | 'thinking' | 'ready';

export function useChatStream() {
  const queryClient = useQueryClient();
  const { sessionUuid, language } = useTouristStore();

  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingUserMessage, setStreamingUserMessage] = useState<string | null>(null);
  const [streamingAnswer, setStreamingAnswer] = useState<string>('');
  const [streamingCitations, setStreamingCitations] = useState<PublicCitationItem[]>([]);
  const [streamingError, setStreamingError] = useState<string | null>(null);
  const [streamingRequestId, setStreamingRequestId] = useState<string | null>(null);
  const [voiceStage, setVoiceStage] = useState<VoiceProcessingStage>('idle');

  const abortControllerRef = useRef<AbortController | null>(null);

  const abortTurn = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setStreamingError('Response generation was stopped.');
  }, []);

  const sendStreamingTurn = useCallback(
    async (messageText: string) => {
      if (!sessionUuid || !messageText.trim() || isStreaming) return;

      const trimmed = messageText.trim();
      setStreamingUserMessage(trimmed);
      setStreamingAnswer('');
      setStreamingCitations([]);
      setStreamingError(null);
      setStreamingRequestId(null);
      setIsStreaming(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        let accumulatedText = '';

        await streamChatTurn(
          sessionUuid,
          trimmed,
          {
            onToken: (token) => {
              accumulatedText += token;
              setStreamingAnswer(accumulatedText);
            },
            onCitations: (citations) => {
              setStreamingCitations(citations);
            },
            onDone: (doneMeta) => {
              // Commit completed turn to TanStack Query session history
              const userItem: SessionHistoryItem = {
                id: `user-${Date.now()}`,
                role: 'user',
                content: trimmed,
                created_at: new Date().toISOString(),
              };
              const assistantItem: SessionHistoryItem = {
                id: doneMeta.message_id,
                role: 'assistant',
                content: accumulatedText,
                created_at: new Date().toISOString(),
              };

              queryClient.setQueryData(['sessionHistory', sessionUuid], (old: any) => {
                const prev = old?.messages || [];
                return {
                  ...(old || { session_uuid: sessionUuid, language_code: language }),
                  total_messages: prev.length + 2,
                  messages: [...prev, userItem, assistantItem],
                };
              });

              // Clean up streaming ephemeral state
              setStreamingUserMessage(null);
              setStreamingAnswer('');
              setStreamingCitations([]);
              setIsStreaming(false);
            },
            onError: (err) => {
              setStreamingError(err.message || 'Stream terminated with an error');
              setStreamingRequestId(err.request_id || null);
              setIsStreaming(false);
            },
          },
          controller.signal
        );
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          if (err instanceof ApiError) {
            setStreamingError(err.message);
            setStreamingRequestId(err.requestId || null);
          } else {
            setStreamingError(err.message || 'Failed to communicate with AI guide');
          }
        }
        setIsStreaming(false);
      } finally {
        abortControllerRef.current = null;
      }
    },
    [sessionUuid, isStreaming, language, queryClient]
  );

  // Non-streaming voice turn (/chat/voice)
  const sendVoiceTurn = useCallback(
    async (audioBlob: Blob, filename: string) => {
      if (!sessionUuid || isStreaming) return;

      setVoiceStage('transcribing');
      setStreamingError(null);
      setStreamingRequestId(null);

      try {
        setVoiceStage('thinking');
        const res = await sendVoiceChatTurn(sessionUuid, audioBlob, filename, language);

        // Commit turn to cache
        const userItem: SessionHistoryItem = {
          id: `user-${Date.now()}`,
          role: 'user',
          content: res.transcription.text,
          created_at: new Date().toISOString(),
        };
        const assistantItem: SessionHistoryItem = {
          id: res.chat.message_id,
          role: 'assistant',
          content: res.chat.answer,
          created_at: res.chat.created_at,
        };

        queryClient.setQueryData(['sessionHistory', sessionUuid], (old: any) => {
          const prev = old?.messages || [];
          return {
            ...(old || { session_uuid: sessionUuid, language_code: language }),
            total_messages: prev.length + 2,
            messages: [...prev, userItem, assistantItem],
          };
        });

        setVoiceStage('ready');
      } catch (err: any) {
        if (err instanceof ApiError) {
          setStreamingError(err.message);
          setStreamingRequestId(err.requestId || null);
        } else {
          setStreamingError(err.message || 'Voice request failed');
        }
        setVoiceStage('idle');
      } finally {
        setTimeout(() => setVoiceStage('idle'), 1000);
      }
    },
    [sessionUuid, isStreaming, language, queryClient]
  );

  return {
    isStreaming,
    streamingUserMessage,
    streamingAnswer,
    streamingCitations,
    streamingError,
    streamingRequestId,
    voiceStage,
    sendStreamingTurn,
    sendVoiceTurn,
    abortTurn,
  };
}
