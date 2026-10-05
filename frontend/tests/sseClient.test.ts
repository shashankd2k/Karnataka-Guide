import { describe, it, expect, vi, beforeEach } from 'vitest';
import { streamChatTurn } from '../src/services/sseClient';

function createMockReadableStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let index = 0;

  return new ReadableStream<Uint8Array>({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]));
        index++;
      } else {
        controller.close();
      }
    },
  });
}

describe('SSE Client Stream Processor', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('correctly processes token, citations, and done events in chunks', async () => {
    const sseChunks = [
      'event: token\ndata: {"text": "King "}\n\n',
      'event: token\r\ndata: {"text": "Vishnuvardhana"}\r\n\r\n',
      'event: citations\ndata: [{"citation_label": "[1]", "source_filename": "Belur.pdf", "page_number": 1}]\n\n',
      'event: done\ndata: {"session_uuid": "test-uuid", "message_id": "msg-1", "grounded": true, "language": "en", "duration_ms": 120}\n\n',
    ];

    const mockStream = createMockReadableStream(sseChunks);

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'Content-Type': 'text/event-stream' }),
      body: mockStream,
    } as unknown as Response);

    const tokensReceived: string[] = [];
    let citationsReceived: any[] = [];
    let donePayload: any = null;

    await streamChatTurn('test-uuid', 'Who built Belur?', {
      onToken: (token) => tokensReceived.push(token),
      onCitations: (citations) => {
        citationsReceived = citations;
      },
      onDone: (doneMeta) => {
        donePayload = doneMeta;
      },
    });

    expect(tokensReceived).toEqual(['King ', 'Vishnuvardhana']);
    expect(citationsReceived).toHaveLength(1);
    expect(citationsReceived[0].citation_label).toBe('[1]');
    expect(donePayload.message_id).toBe('msg-1');
    expect(donePayload.grounded).toBe(true);
  });

  it('handles chunk boundaries splitting event name and data lines', async () => {
    // Split across chunk boundaries
    const fragmentedChunks = [
      'event: tok',
      'en\ndata: {"text": "Hampi "}\n\n',
      'event: done\ndata: {"session_uuid": "uuid-1", "message_id": "done-1", "grounded": true, "language": "en", "duration_ms": 50}\n\n',
    ];

    const mockStream = createMockReadableStream(fragmentedChunks);

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'Content-Type': 'text/event-stream' }),
      body: mockStream,
    } as unknown as Response);

    const tokens: string[] = [];
    let doneCalled = false;

    await streamChatTurn('uuid-1', 'Tell me about Hampi', {
      onToken: (tok) => tokens.push(tok),
      onDone: () => {
        doneCalled = true;
      },
    });

    expect(tokens).toEqual(['Hampi ']);
    expect(doneCalled).toBe(true);
  });

  it('triggers onError callback when backend emits error event', async () => {
    const errorChunks = [
      'event: error\ndata: {"error_code": "RAG_ERROR", "message": "Failed to retrieve context", "request_id": "req-123"}\n\n',
    ];

    const mockStream = createMockReadableStream(errorChunks);

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ 'Content-Type': 'text/event-stream' }),
      body: mockStream,
    } as unknown as Response);

    let errorReceived: any = null;

    await streamChatTurn('uuid-1', 'Query', {
      onError: (err) => {
        errorReceived = err;
      },
    });

    expect(errorReceived).not.toBeNull();
    expect(errorReceived.error_code).toBe('RAG_ERROR');
    expect(errorReceived.message).toBe('Failed to retrieve context');
    expect(errorReceived.request_id).toBe('req-123');
  });

  it('handles client abort cleanly without throwing unexpected error', async () => {
    const controller = new AbortController();

    global.fetch = vi.fn().mockImplementation(() => {
      controller.abort();
      const err = new Error('The operation was aborted.');
      err.name = 'AbortError';
      return Promise.reject(err);
    });

    await expect(
      streamChatTurn('uuid-1', 'Query', {}, controller.signal)
    ).resolves.toBeUndefined();
  });
});
