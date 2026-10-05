export type LanguageCode = 'en' | 'kn';

export interface SessionResponse {
  session_uuid: string;
  language_code: LanguageCode;
  created_at: string;
}

export interface PublicCitationItem {
  citation_label: string;
  source_filename: string;
  page_number: number;
  section_header?: string | null;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  language?: string;
  grounded?: boolean;
  citations?: PublicCitationItem[];
  isStreaming?: boolean;
  isError?: boolean;
}

export interface SessionHistoryItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface SessionHistoryResponse {
  session_uuid: string;
  language_code: LanguageCode;
  total_messages: number;
  messages: SessionHistoryItem[];
}

export interface DeleteSessionResponse {
  session_uuid: string;
  deleted_messages_count: number;
  message: string;
}

export interface ChatTurnRequest {
  session_uuid: string;
  message: string;
}

export interface ChatTurnResponse {
  session_uuid: string;
  message_id: string;
  answer: string;
  language: string;
  grounded: boolean;
  citations: PublicCitationItem[];
  retrieval?: {
    resolved_query?: string;
    evidence_count?: number;
    latency_ms?: number;
  };
  created_at: string;
}

export interface TranscriptionSegment {
  start: number;
  end: number;
  text: string;
}

export interface TranscriptionResponse {
  text: string;
  language: string;
  language_probability: number;
  duration_seconds: number;
  segments: TranscriptionSegment[];
}

export interface VoiceChatResponse {
  transcription: TranscriptionResponse;
  chat: ChatTurnResponse;
}

export interface StreamDoneMeta {
  session_uuid: string;
  message_id: string;
  grounded: boolean;
  language: string;
  duration_ms: number;
}

export interface StreamErrorMeta {
  code: string;
  message: string;
  request_id?: string;
}

export interface Destination {
  slug: string;
  name: string;
  kannadaName: string;
  district: string;
  dynasty: string;
  century: string;
  shortDescription: string;
  kannadaDescription: string;
  coordinates: [number, number]; // [lat, lng]
  category: string;
  tags: string[];
  imageAsset: string;
  suggestedQueries: { en: string; kn: string }[];
}
