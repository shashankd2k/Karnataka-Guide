import { PublicCitationItem, StreamDoneMeta, StreamErrorMeta } from '../types/tourist';
import { ApiError } from './apiClient';

export interface SSECallbacks {
  onToken?: (text: string) => void;
  onCitations?: (citations: PublicCitationItem[]) => void;
  onDone?: (meta: StreamDoneMeta) => void;
  onError?: (error: StreamErrorMeta) => void;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function streamChatTurn(
  sessionUuid: string,
  message: string,
  callbacks: SSECallbacks,
  signal?: AbortSignal
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/tourist/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({ session_uuid: sessionUuid, message }),
      signal,
    });
  } catch (err: any) {
    if (err.name === 'AbortError' || signal?.aborted) {
      return; // Clean client-side abort
    }
    throw err;
  }

  if (!response.ok) {
    let errorCode = 'STREAM_INIT_FAILED';
    let errorMessage = `HTTP Error ${response.status}`;
    let requestId: string | undefined;

    try {
      const errJson = await response.json();
      if (errJson.error) {
        errorCode = errJson.error.code || errorCode;
        errorMessage = errJson.error.message || errorMessage;
        requestId = errJson.error.request_id;
      }
    } catch {
      // Ignored
    }

    throw new ApiError(response.status, errorCode, errorMessage, requestId);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('ReadableStream not supported by browser environment');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  const processFrame = (frame: string) => {
    const trimmed = frame.trim();
    if (!trimmed) return;

    const lines = trimmed.split('\n');
    let eventType = 'message';
    let dataStr = '';

    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith('data:')) {
        const chunk = line.slice(5).trim();
        dataStr = dataStr ? `${dataStr}\n${chunk}` : chunk;
      }
    }

    if (!dataStr) return;

    try {
      const data = JSON.parse(dataStr);

      if (eventType === 'token') {
        if (typeof data.text === 'string') {
          callbacks.onToken?.(data.text);
        }
      } else if (eventType === 'citations') {
        if (Array.isArray(data)) {
          callbacks.onCitations?.(data);
        } else if (Array.isArray(data.citations)) {
          callbacks.onCitations?.(data.citations);
        }
      } else if (eventType === 'done') {
        callbacks.onDone?.(data as StreamDoneMeta);
      } else if (eventType === 'error') {
        callbacks.onError?.(data as StreamErrorMeta);
      }
    } catch (e) {
      console.warn('Failed to parse SSE JSON payload:', dataStr, e);
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const normalized = buffer.replace(/\r\n/g, '\n');
      const parts = normalized.split('\n\n');
      buffer = parts.pop() || '';

      for (const frame of parts) {
        processFrame(frame);
      }
    }

    // Final stream flush
    buffer += decoder.decode();
    if (buffer.trim()) {
      const normalized = buffer.replace(/\r\n/g, '\n');
      const remainingFrames = normalized.split('\n\n');
      for (const frame of remainingFrames) {
        processFrame(frame);
      }
    }
  } catch (err: any) {
    if (err.name === 'AbortError' || signal?.aborted) {
      return; // Clean client abort
    }
    throw err;
  }
}
