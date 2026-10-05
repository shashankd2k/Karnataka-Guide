import { useState, useRef, useCallback, useEffect } from 'react';
import { synthesizeSpeech } from '../services/apiClient';
import { useTouristStore } from '../stores/touristStore';

export type AudioState = 'idle' | 'loading' | 'playing' | 'paused';

export function useAudioPlayer() {
  const { sessionUuid } = useTouristStore();
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [audioState, setAudioState] = useState<AudioState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentBlobUrlRef = useRef<string | null>(null);

  const cleanupAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    if (currentBlobUrlRef.current) {
      URL.revokeObjectURL(currentBlobUrlRef.current);
      currentBlobUrlRef.current = null;
    }
    setPlayingMessageId(null);
    setAudioState('idle');
  }, []);

  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, [cleanupAudio]);

  const playAssistantAudio = useCallback(
    async (assistantMessageId: string) => {
      if (!sessionUuid || !assistantMessageId) return;

      // Toggle pause/play if same message is already loaded
      if (playingMessageId === assistantMessageId && audioRef.current) {
        if (audioState === 'playing') {
          audioRef.current.pause();
          setAudioState('paused');
        } else {
          audioRef.current.play().catch(() => setAudioState('paused'));
          setAudioState('playing');
        }
        return;
      }

      // Switching to a new message
      cleanupAudio();
      setPlayingMessageId(assistantMessageId);
      setAudioState('loading');
      setErrorMessage(null);

      try {
        const audioBlob = await synthesizeSpeech(sessionUuid, assistantMessageId);
        const blobUrl = URL.createObjectURL(audioBlob);
        currentBlobUrlRef.current = blobUrl;

        const audio = new Audio(blobUrl);
        audioRef.current = audio;

        audio.onplay = () => setAudioState('playing');
        audio.onpause = () => {
          if (audio.ended) {
            cleanupAudio();
          } else {
            setAudioState('paused');
          }
        };
        audio.onended = () => {
          cleanupAudio();
        };
        audio.onerror = () => {
          setErrorMessage('Audio playback error');
          cleanupAudio();
        };

        await audio.play();
      } catch (err: any) {
        console.error('TTS synthesis failed:', err);
        setErrorMessage(err.message || 'Failed to synthesize audio');
        cleanupAudio();
      }
    },
    [sessionUuid, playingMessageId, audioState, cleanupAudio]
  );

  const stopAudio = useCallback(() => {
    cleanupAudio();
  }, [cleanupAudio]);

  return {
    playingMessageId,
    audioState,
    errorMessage,
    playAssistantAudio,
    stopAudio,
  };
}
