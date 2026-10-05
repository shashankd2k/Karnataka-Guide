import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createSession,
  getSessionHistory,
  deleteSessionHistory,
  sendChatTurn,
  transcribeVoice,
  sendVoiceChatTurn,
  synthesizeSpeech,
  ApiError,
} from '../src/services/apiClient';

describe('API Client Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('createSession creates an anonymous session with language', async () => {
    const mockResponse = {
      session_uuid: '11111111-2222-3333-4444-555555555555',
      language_code: 'kn',
      created_at: '2026-09-01T12:00:00Z',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const result = await createSession('kn');
    expect(result.session_uuid).toBe(mockResponse.session_uuid);
    expect(result.language_code).toBe('kn');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/tourist/sessions', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language_code: 'kn' }),
    }));
  });

  it('getSessionHistory fetches historical messages', async () => {
    const mockHistory = {
      session_uuid: 'test-uuid',
      language_code: 'en',
      total_messages: 2,
      messages: [
        { id: '1', role: 'user', content: 'Hi', created_at: '2026-09-01T12:00:00Z' },
        { id: '2', role: 'assistant', content: 'Hello!', created_at: '2026-09-01T12:00:01Z' },
      ],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockHistory,
    } as Response);

    const result = await getSessionHistory('test-uuid');
    expect(result.total_messages).toBe(2);
    expect(result.messages).toHaveLength(2);
  });

  it('deleteSessionHistory clears conversation', async () => {
    const mockDelete = {
      session_uuid: 'test-uuid',
      deleted_messages_count: 4,
      message: 'Session history deleted successfully',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockDelete,
    } as Response);

    const result = await deleteSessionHistory('test-uuid');
    expect(result.deleted_messages_count).toBe(4);
  });

  it('sendChatTurn sends non-streaming turn and returns answer', async () => {
    const mockTurn = {
      session_uuid: 'test-uuid',
      message_id: 'msg-123',
      answer: 'Belur temple was commissioned by King Vishnuvardhana [1].',
      citations: [
        {
          citation_label: '[1]',
          source_filename: 'Belur.pdf',
          page_number: 1,
        },
      ],
      grounded: true,
      language: 'en',
      duration_ms: 250,
      created_at: '2026-09-01T12:00:02Z',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTurn,
    } as Response);

    const result = await sendChatTurn('test-uuid', 'Who built Belur?');
    expect(result.message_id).toBe('msg-123');
    expect(result.citations).toHaveLength(1);
    expect(result.grounded).toBe(true);
  });

  it('transcribeVoice uploads audio file and returns transcription', async () => {
    const mockTranscribe = {
      text: 'Tell me about Halebidu',
      language: 'en',
      duration: 3.2,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockTranscribe,
    } as Response);

    const blob = new Blob(['dummy audio bytes'], { type: 'audio/webm' });
    const result = await transcribeVoice(blob, 'sample.webm', 'en');
    expect(result.text).toBe('Tell me about Halebidu');
    expect(result.language).toBe('en');
  });

  it('sendVoiceChatTurn executes immediate voice turn', async () => {
    const mockVoiceChat = {
      transcription: {
        text: 'Who built Belur?',
        language: 'en',
        duration: 2.1,
      },
      chat: {
        session_uuid: 'test-uuid',
        message_id: 'assistant-456',
        answer: 'King Vishnuvardhana commissioned the temple in 1117 CE [1].',
        citations: [],
        grounded: true,
        language: 'en',
        duration_ms: 400,
        created_at: '2026-09-01T12:00:05Z',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockVoiceChat,
    } as Response);

    const blob = new Blob(['dummy audio'], { type: 'audio/webm' });
    const result = await sendVoiceChatTurn('test-uuid', blob, 'query.webm', 'en');
    expect(result.transcription.text).toBe('Who built Belur?');
    expect(result.chat.message_id).toBe('assistant-456');
    expect(result.chat.grounded).toBe(true);
  });

  it('synthesizeSpeech returns binary audio blob', async () => {
    const mockBlob = new Blob(['RIFF....WAVEfmt '], { type: 'audio/wav' });

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () => mockBlob,
    } as Response);

    const blob = await synthesizeSpeech('test-uuid', 'msg-123');
    expect(blob.type).toBe('audio/wav');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/tourist/voice/synthesize', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        session_uuid: 'test-uuid',
        assistant_message_id: 'msg-123',
      }),
    }));
  });

  it('throws ApiError with structured detail on 4xx/5xx responses', async () => {
    const errorBody = {
      detail: {
        error_code: 'SESSION_NOT_FOUND',
        message: 'Session does not exist',
        request_id: 'req-999',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => errorBody,
    } as Response);

    await expect(getSessionHistory('invalid-uuid')).rejects.toThrow(ApiError);
  });
});
