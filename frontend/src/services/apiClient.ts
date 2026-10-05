import {
  SessionResponse,
  SessionHistoryResponse,
  DeleteSessionResponse,
  ChatTurnResponse,
  TranscriptionResponse,
  VoiceChatResponse,
  LanguageCode,
} from '../types/tourist';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorCode = 'UNKNOWN_ERROR';
    let errorMessage = `HTTP Error ${res.status}`;
    let requestId: string | undefined;

    try {
      const errJson = await res.json();
      if (errJson.error) {
        errorCode = errJson.error.code || errorCode;
        errorMessage = errJson.error.message || errorMessage;
        requestId = errJson.error.request_id;
      }
    } catch {
      // Body not JSON
    }

    throw new ApiError(res.status, errorCode, errorMessage, requestId);
  }
  return res.json() as Promise<T>;
}

export async function createSession(languageCode?: LanguageCode): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/tourist/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(languageCode ? { language_code: languageCode } : {}),
  });
  return handleResponse<SessionResponse>(res);
}

export async function getSessionHistory(
  sessionUuid: string,
  limit: number = 50
): Promise<SessionHistoryResponse> {
  const res = await fetch(`${API_BASE}/tourist/sessions/${sessionUuid}?limit=${limit}`);
  return handleResponse<SessionHistoryResponse>(res);
}

export async function deleteSessionHistory(sessionUuid: string): Promise<DeleteSessionResponse> {
  const res = await fetch(`${API_BASE}/tourist/sessions/${sessionUuid}`, {
    method: 'DELETE',
  });
  return handleResponse<DeleteSessionResponse>(res);
}

export async function sendChatTurn(
  sessionUuid: string,
  message: string
): Promise<ChatTurnResponse> {
  const res = await fetch(`${API_BASE}/tourist/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_uuid: sessionUuid, message }),
  });
  return handleResponse<ChatTurnResponse>(res);
}

export async function transcribeVoice(
  audioBlob: Blob,
  filename: string,
  language?: string
): Promise<TranscriptionResponse> {
  const formData = new FormData();
  formData.append('file', audioBlob, filename);
  if (language) formData.append('language', language);

  const res = await fetch(`${API_BASE}/tourist/voice/transcribe`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<TranscriptionResponse>(res);
}

export async function sendVoiceChatTurn(
  sessionUuid: string,
  audioBlob: Blob,
  filename: string,
  language?: string
): Promise<VoiceChatResponse> {
  const formData = new FormData();
  formData.append('session_uuid', sessionUuid);
  formData.append('file', audioBlob, filename);
  if (language) formData.append('language', language);

  const res = await fetch(`${API_BASE}/tourist/chat/voice`, {
    method: 'POST',
    body: formData,
  });
  return handleResponse<VoiceChatResponse>(res);
}

export async function synthesizeSpeech(
  sessionUuid: string,
  assistantMessageId: string
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/tourist/voice/synthesize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_uuid: sessionUuid,
      assistant_message_id: assistantMessageId,
    }),
  });

  if (!res.ok) {
    let errorCode = 'SYNTHESIS_FAILED';
    let errorMessage = 'Audio synthesis failed';
    try {
      const errJson = await res.json();
      if (errJson.error) {
        errorCode = errJson.error.code || errorCode;
        errorMessage = errJson.error.message || errorMessage;
      }
    } catch {
      // Ignored
    }
    throw new ApiError(res.status, errorCode, errorMessage);
  }

  return res.blob();
}
