import { useState, useRef, useCallback, useEffect } from 'react';

const PREFERRED_MIMES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
  'audio/wav',
];

function resolveExtensionFromMime(mime: string): string | null {
  const lower = mime.toLowerCase();
  if (lower.includes('webm')) return 'webm';
  if (lower.includes('ogg')) return 'ogg';
  if (lower.includes('mp4') || lower.includes('m4a')) return 'mp4';
  if (lower.includes('wav')) return 'wav';
  return null;
}

export function useVoiceRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [durationSeconds, setDurationSeconds] = useState(0);
  const [waveformBars, setWaveformBars] = useState<number[]>([0.1, 0.1, 0.1, 0.1, 0.1]);
  const [recordingError, setRecordingError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const timerRef = useRef<number | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // Cleanup audio tracks and context
  const cleanup = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (timerRef.current) clearInterval(timerRef.current);

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    analyserRef.current = null;
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    setIsRecording(false);
    setDurationSeconds(0);
    setWaveformBars([0.1, 0.1, 0.1, 0.1, 0.1]);
  }, []);

  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  const startRecording = useCallback(async () => {
    cleanup();
    setRecordingError(null);

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setRecordingError('Microphone audio recording is not supported in this browser.');
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Audio analysis for frequency waveform
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Select supported candidate or allow browser default
      let chosenMime: string | undefined;
      for (const candidate of PREFERRED_MIMES) {
        if (MediaRecorder.isTypeSupported(candidate)) {
          chosenMime = candidate;
          break;
        }
      }

      const recorder = chosenMime
        ? new MediaRecorder(stream, { mimeType: chosenMime })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      recorder.start(100); // 100ms timeslices
      setIsRecording(true);

      // Duration timer
      let elapsed = 0;
      timerRef.current = window.setInterval(() => {
        elapsed += 1;
        setDurationSeconds(elapsed);
        if (elapsed >= 60) {
          // Auto-stop at 60s
          recorder.stop();
        }
      }, 1000);

      // Waveform animation loop
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateWaveform = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        // Extract 5 representative frequency levels
        const b1 = Math.max(0.1, (dataArray[2] || 0) / 255);
        const b2 = Math.max(0.1, (dataArray[5] || 0) / 255);
        const b3 = Math.max(0.1, (dataArray[8] || 0) / 255);
        const b4 = Math.max(0.1, (dataArray[12] || 0) / 255);
        const b5 = Math.max(0.1, (dataArray[16] || 0) / 255);

        setWaveformBars([b1, b2, b3, b4, b5]);
        animFrameRef.current = requestAnimationFrame(updateWaveform);
      };
      updateWaveform();
    } catch (err: any) {
      console.error('Error accessing microphone:', err);
      setRecordingError(err.message || 'Permission denied or microphone unavailable.');
      cleanup();
    }
  }, [cleanup]);

  const stopRecording = useCallback((): Promise<{ blob: Blob; filename: string } | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === 'inactive') {
        cleanup();
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const actualMime = recorder.mimeType || 'audio/webm';
        const extension = resolveExtensionFromMime(actualMime);

        if (!extension) {
          setRecordingError(`Browser recorded unsupported audio format (${actualMime}).`);
          cleanup();
          resolve(null);
          return;
        }

        const audioBlob = new Blob(chunksRef.current, { type: actualMime });
        const filename = `tourist_voice_${Date.now()}.${extension}`;

        cleanup();
        resolve({ blob: audioBlob, filename });
      };

      recorder.stop();
    });
  }, [cleanup]);

  const cancelRecording = useCallback(() => {
    cleanup();
  }, [cleanup]);

  return {
    isRecording,
    durationSeconds,
    waveformBars,
    recordingError,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
