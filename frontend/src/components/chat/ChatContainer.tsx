import React, { useState } from 'react';
import { useSession } from '../../hooks/useSession';
import { useChatStream } from '../../hooks/useChatStream';
import { useVoiceRecorder } from '../../hooks/useVoiceRecorder';
import { useAudioPlayer } from '../../hooks/useAudioPlayer';
import { useTouristStore } from '../../stores/touristStore';
import { Sidebar } from '../layout/Sidebar';
import { MessageList } from './MessageList';
import { ChatComposer } from './ChatComposer';
import { SuggestionPills } from './SuggestionPills';
import { VoiceRecorderModal } from '../voice/VoiceRecorderModal';
import { CitationDrawer } from '../citations/CitationDrawer';
import { Menu, AlertCircle, Loader2 } from 'lucide-react';

export const ChatContainer: React.FC = () => {
  const { language, activeDrawer, setActiveDrawer } = useTouristStore();
  const { history, clearHistory, isClearing } = useSession();

  const {
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
  } = useChatStream();

  const {
    isRecording,
    durationSeconds,
    waveformBars,
    recordingError,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecorder();

  const { playingMessageId, audioState, playAssistantAudio } = useAudioPlayer();

  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const [statusAnnouncement, setStatusAnnouncement] = useState<string>('');

  const handleOpenVoice = async () => {
    setIsVoiceModalOpen(true);
    await startRecording();
  };

  const handleStopVoice = async () => {
    const recorded = await stopRecording();
    setIsVoiceModalOpen(false);

    if (recorded && recorded.blob) {
      await sendVoiceTurn(recorded.blob, recorded.filename);
      setStatusAnnouncement('Voice question processed. Assistant answer ready.');
    }
  };

  const handleCancelVoice = () => {
    cancelRecording();
    setIsVoiceModalOpen(false);
  };

  const handleSendPrompt = (prompt: string) => {
    sendStreamingTurn(prompt);
  };

  return (
    <div className="flex-1 flex w-full h-[calc(100vh-4rem-4rem)] md:h-[calc(100vh-4rem)] overflow-hidden">
      {/* Screen Reader Live Region for accessible announcements */}
      <div className="sr-only" role="status" aria-live="polite">
        {statusAnnouncement}
      </div>

      {/* Desktop Left Sidebar */}
      <div className="hidden lg:block w-64 shrink-0 h-full">
        <Sidebar
          onSelectPrompt={handleSendPrompt}
          onClearHistory={clearHistory}
          isClearing={isClearing}
        />
      </div>

      {/* Mobile/Tablet Slide-over Sidebar */}
      {activeDrawer === 'sidebar' && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/50 backdrop-blur-xs" onClick={() => setActiveDrawer('none')} />
          <div className="relative w-72 max-w-[80vw] h-full z-10">
            <Sidebar
              onSelectPrompt={handleSendPrompt}
              onClearHistory={clearHistory}
              isClearing={isClearing}
              onClose={() => setActiveDrawer('none')}
            />
          </div>
        </div>
      )}

      {/* Main Conversation Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden bg-ivory/30 dark:bg-night-slate/30">
        {/* Top Mobile Bar Toggle & Voice Stage Banner */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-temple-gold/15 bg-ivory/60 dark:bg-night-slate/60 text-xs">
          <button
            type="button"
            onClick={() => setActiveDrawer('sidebar')}
            className="lg:hidden flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-temple-gold/30 hover:bg-temple-gold/10 text-deep-brown dark:text-ivory"
          >
            <Menu className="w-4 h-4 text-temple-gold" />
            <span>{language === 'kn' ? 'ಮೆನು' : 'Menu'}</span>
          </button>

          {voiceStage !== 'idle' && (
            <div className="flex items-center gap-2 text-temple-gold font-medium">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>
                {voiceStage === 'transcribing'
                  ? (language === 'kn' ? 'ಧ್ವನಿ ಗುರುತಿಸಲಾಗುತ್ತಿದೆ (STT)...' : 'Transcribing voice...')
                  : (language === 'kn' ? 'ಮಾಹಿತಿ ವಿಶ್ಲೇಷಿಸಲಾಗುತ್ತಿದೆ (RAG)...' : 'Thinking & retrieving facts...')}
              </span>
            </div>
          )}
        </div>

        {/* Streaming Error Notice */}
        {streamingError && (
          <div className="mx-4 mt-2 p-3 rounded-xl bg-crimson-rubric/10 border border-crimson-rubric/30 text-crimson-rubric text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{streamingError}</span>
            </div>
            {streamingRequestId && (
              <span className="font-mono text-[10px] opacity-70">
                ID: {streamingRequestId.slice(0, 8)}
              </span>
            )}
          </div>
        )}

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto">
          <MessageList
            history={history}
            isStreaming={isStreaming}
            streamingUserMessage={streamingUserMessage}
            streamingAnswer={streamingAnswer}
            streamingCitations={streamingCitations}
            playingMessageId={playingMessageId}
            audioState={audioState}
            onTogglePlayAudio={playAssistantAudio}
            onAbortStream={abortTurn}
            onSelectPrompt={handleSendPrompt}
          />
        </div>

        {/* Footer Composer & Suggestion Pills */}
        <div className="p-3 sm:p-4 border-t border-temple-gold/20 bg-ivory/80 dark:bg-night-slate/90 space-y-2">
          <SuggestionPills onSelectPrompt={handleSendPrompt} disabled={isStreaming} />
          <ChatComposer
            onSendMessage={handleSendPrompt}
            onOpenVoiceModal={handleOpenVoice}
            isStreaming={isStreaming}
            onAbort={abortTurn}
            disabled={voiceStage !== 'idle' || isRecording}
          />
        </div>
      </div>

      {/* Right Collapsible Citation Drawer */}
      {activeDrawer === 'citations' && (
        <CitationDrawer
          citations={streamingCitations.length > 0 ? streamingCitations : []}
          onClose={() => setActiveDrawer('none')}
        />
      )}

      {/* Voice Recorder Modal */}
      <VoiceRecorderModal
        isOpen={isVoiceModalOpen}
        durationSeconds={durationSeconds}
        waveformBars={waveformBars}
        recordingError={recordingError}
        onStop={handleStopVoice}
        onCancel={handleCancelVoice}
      />
    </div>
  );
};
