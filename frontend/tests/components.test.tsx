import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitationPill } from '../src/components/citations/CitationPill';
import { TTSPlayerButton } from '../src/components/voice/TTSPlayerButton';
import { AssistantMessage } from '../src/components/chat/AssistantMessage';
import { EmptyChatState } from '../src/components/chat/EmptyChatState';
import { SuggestionPills } from '../src/components/chat/SuggestionPills';

describe('UI Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders CitationPill and handles click', () => {
    const citations = [
      {
        citation_label: '[1]',
        source_filename: 'Belur.pdf',
        page_number: 1,
      },
    ];

    render(<CitationPill label="[1]" citations={citations} />);
    const button = screen.getByRole('button', { name: /view citation \[1\]/i });
    expect(button).toBeDefined();
    expect(button.textContent).toBe('[1]');
  });

  it('renders TTSPlayerButton in idle, loading, and playing states', () => {
    const toggleMock = vi.fn();

    // Idle
    const { rerender } = render(
      <TTSPlayerButton
        assistantMessageId="msg-1"
        isPlaying={false}
        isLoading={false}
        onTogglePlay={toggleMock}
      />
    );
    expect(screen.getByText('Listen')).toBeDefined();

    // Click toggle
    fireEvent.click(screen.getByRole('button'));
    expect(toggleMock).toHaveBeenCalledWith('msg-1');

    // Loading
    rerender(
      <TTSPlayerButton
        assistantMessageId="msg-1"
        isPlaying={false}
        isLoading={true}
        onTogglePlay={toggleMock}
      />
    );
    expect(screen.getByText('Synthesizing...')).toBeDefined();

    // Playing
    rerender(
      <TTSPlayerButton
        assistantMessageId="msg-1"
        isPlaying={true}
        isLoading={false}
        onTogglePlay={toggleMock}
      />
    );
    expect(screen.getByText('Pause')).toBeDefined();
  });

  it('renders AssistantMessage with grounded badge and formatted citation pills', () => {
    const citations = [
      {
        citation_label: '[1]',
        source_filename: 'Belur.pdf',
        page_number: 2,
      },
    ];

    render(
      <AssistantMessage
        id="msg-1"
        content="King Vishnuvardhana built the temple in 1117 CE [1]."
        citations={citations}
        grounded={true}
      />
    );

    expect(screen.getByText('Grounded')).toBeDefined();
    expect(screen.getByText('[1]')).toBeDefined();
  });

  it('renders EmptyChatState with starter prompts', () => {
    const onSelectMock = vi.fn();
    render(<EmptyChatState onSelectPrompt={onSelectMock} />);

    expect(screen.getByText('Karnataka Heritage AI Guide')).toBeDefined();
    expect(screen.getByText('Belur Chennakeshava')).toBeDefined();

    fireEvent.click(screen.getByText('Belur Chennakeshava'));
    expect(onSelectMock).toHaveBeenCalled();
  });

  it('renders SuggestionPills and handles selection', () => {
    const onSelectMock = vi.fn();
    render(<SuggestionPills onSelectPrompt={onSelectMock} />);

    const pill = screen.getByText(/Who built the Belur Chennakeshava temple\?/i);
    expect(pill).toBeDefined();

    fireEvent.click(pill);
    expect(onSelectMock).toHaveBeenCalledWith('Who built the Belur Chennakeshava temple?');
  });
});
