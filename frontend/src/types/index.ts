// Type definitions for the chatbot SaaS application

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  date_joined: string;
}

export interface Chatbot {
  id: string;
  name: string;
  description: string;
  public_url_slug: string;
  status: 'draft' | 'training' | 'completed' | 'error' | 'active' | 'processing' | 'pending';
  created_at: string;
  updated_at: string;
  conversation_count?: number;
  total_conversations?: number;
  total_messages?: number;
  settings?: ChatbotSettings;
  welcome_message?: string;
  placeholder_text?: string;
  theme_color?: string;
  temperature?: number;
  max_tokens?: number;
  model_name?: string;
  enable_citations?: boolean;
  enable_data_collection?: boolean;
  is_ready?: boolean;
  public_url?: string;
  embed_url?: string;
  embed_script?: string;
  has_knowledge_sources?: boolean;
  last_trained_at?: string | null;
  metadata?: any;
}

export interface ChatbotSettings {
  rate_limit_messages_per_hour: number;
  enable_lead_capture: boolean;
  lead_capture_trigger: string;
  lead_capture_message: string;
  show_powered_by: boolean;
  custom_css: string;
  temperature: number;
  max_response_tokens: number;
}

export interface Conversation {
  id: string;
  chatbot: string;
  chatbot_id?: string;
  user_id?: string;
  session_id: string;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  message_count: number;
  lead_email?: string;
  lead_name?: string;
  user_satisfaction?: number;
}

export interface Message {
  id: string;
  conversation: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  metadata?: any;
  citations?: string[];
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user?: User;
  expires_in?: number;
}

export interface RegisterResponse {
  message: string;
  access_token: string;
  refresh_token: string;
  user: User;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
}

export interface ChatMessage {
  message: string;
  conversation_id?: string;
  language?: string;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
  message_id: string;
  citations?: string[];
  sources?: any[];
  metadata?: any;
}

export interface WebSocketMessage {
  type: 'connection_established' | 'chat_message' | 'typing_indicator' | 'error' | 'pong';
  id?: string;
  role?: 'user' | 'assistant';
  content?: string;
  timestamp?: string;
  citations?: string[];
  metadata?: any;
  message?: string;
  is_typing?: boolean;
  user_identifier?: string;
  chatbot_id?: string;
  conversation_id?: string;
}

export interface ApiError {
  message: string;
  status: number;
  details?: any;
}