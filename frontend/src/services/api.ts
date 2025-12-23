// API service for communicating with Django backend

import { 
  User, 
  Chatbot, 
  Conversation, 
  Message, 
  AuthTokens, 
  LoginRequest, 
  RegisterRequest,
  RegisterResponse,
  ChatMessage,
  ChatResponse
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || '/api/v1';
const AUTH_BASE_URL = (import.meta as any).env?.VITE_AUTH_URL || '/auth';

class ApiError extends Error {
  status: number;
  details?: any;

  constructor(message: string, status: number, details?: any) {
    super(message);
    this.status = status;
    this.details = details;
    this.name = 'ApiError';
  }
}

class ApiService {
  private baseURL: string;
  private authURL: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private accessTokenExpiry: Date | null = null;
  private refreshAttempts = 0;
  private maxRefreshAttempts = 2;
  private isRefreshing = false;
  private refreshPromise: Promise<boolean> | null = null;

  constructor() {
    this.baseURL = API_BASE_URL;
    this.authURL = AUTH_BASE_URL;
    this.loadTokensFromStorage();
  }

  private loadTokensFromStorage() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
    const expiryStr = localStorage.getItem('access_token_expiry');
    
    // Validate loaded tokens
    if (this.accessToken && expiryStr) {
      const expiry = new Date(expiryStr);
      const now = new Date();
      
      if (expiry <= now) {
        // Token expired, clear and optionally try to refresh
        console.log('Access token expired, attempting refresh...');
        if (this.refreshToken) {
          // Try to refresh in the background
          this.refreshAccessToken().catch(() => {
            console.log('Failed to refresh expired token on load');
            this.clearTokensFromStorage();
          });
        } else {
          this.clearTokensFromStorage();
        }
      } else {
        this.accessTokenExpiry = expiry;
      }
    } else if (this.accessToken && !expiryStr) {
      // No expiry stored, assume 15 minutes from now
      this.accessTokenExpiry = new Date(Date.now() + 15 * 60 * 1000);
      localStorage.setItem('access_token_expiry', this.accessTokenExpiry.toISOString());
    }
  }

  private saveTokensToStorage(tokens: AuthTokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    
    // Calculate and store expiry time (default 15 minutes)
    const expiresIn = tokens.expires_in || 900;
    this.accessTokenExpiry = new Date(Date.now() + expiresIn * 1000);
    
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    localStorage.setItem('access_token_expiry', this.accessTokenExpiry.toISOString());
    
    // Reset refresh attempts on successful token save
    this.refreshAttempts = 0;
  }

  private clearTokensFromStorage() {
    this.accessToken = null;
    this.refreshToken = null;
    this.accessTokenExpiry = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('access_token_expiry');
    
    // Reset refresh state
    this.refreshAttempts = 0;
    this.isRefreshing = false;
    this.refreshPromise = null;
  }

  private async ensureValidToken(): Promise<boolean> {
    // If no tokens, can't ensure validity
    if (!this.accessToken || !this.refreshToken) {
      return false;
    }
    
    // If no expiry tracked, assume token is valid (will be caught by 401 if not)
    if (!this.accessTokenExpiry) {
      return true;
    }
    
    const now = new Date();
    // Add 60 second buffer - refresh if token expires in next minute
    const expiryWithBuffer = new Date(this.accessTokenExpiry.getTime() - 60000);
    
    // Check if token needs refresh
    if (now >= expiryWithBuffer) {
      console.log('Access token expiring soon, proactively refreshing...');
      return await this.refreshAccessToken();
    }
    
    return true;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    useAuthURL = false
  ): Promise<T> {
    // Check if token needs refresh before making request (proactive refresh)
    if (this.accessToken && !endpoint.includes('/refresh') && !endpoint.includes('/login') && !endpoint.includes('/register')) {
      await this.ensureValidToken();
    }
    
    const url = `${useAuthURL ? this.authURL : this.baseURL}${endpoint}`;
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string> || {}),
    };

    if (this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    try {
      let response = await fetch(url, config);

      // Handle token refresh on 401 (reactive refresh)
      // But don't refresh if this IS the refresh endpoint (prevent infinite loop)
      if (response.status === 401 && 
          this.refreshToken && 
          !endpoint.includes('/refresh') &&
          !endpoint.includes('/login') &&
          !endpoint.includes('/register')) {
        
        console.log(`Got 401 on ${endpoint}, attempting token refresh...`);
        const refreshed = await this.refreshAccessToken();
        
        if (refreshed) {
          // Retry the original request with new token
          headers.Authorization = `Bearer ${this.accessToken}`;
          response = await fetch(url, { ...config, headers });
        } else {
          // Refresh failed, redirect to login
          console.log('Token refresh failed, redirecting to login...');
          window.location.href = '/login';
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Enhanced error handling with detailed field-level messages
        let errorMessage = `HTTP Error ${response.status}`;
        let fieldErrors: Record<string, any> = {};
        
        if (errorData.error && errorData.details) {
          // Extract field-specific errors for form validation
          const details = errorData.details;
          const errorMessages = [];
          
          for (const field in details) {
            if (details[field] && Array.isArray(details[field])) {
              fieldErrors[field] = details[field];
              errorMessages.push(`${field}: ${details[field].join(', ')}`);
            }
          }
          
          errorMessage = errorMessages.length > 0 ? errorMessages.join('. ') : errorData.error;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        }
        
        // Include field errors in the ApiError for form handling
        const enhancedErrorData = {
          ...errorData,
          fieldErrors
        };
        
        throw new ApiError(errorMessage, response.status, enhancedErrorData);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Network error occurred', 0, error);
    }
  }

  // Authentication methods
  async login(credentials: LoginRequest): Promise<AuthTokens> {
    const tokens = await this.request<AuthTokens>('/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    }, true);
    
    // Ensure we have expires_in from the response
    const tokensWithExpiry = {
      ...tokens,
      expires_in: tokens.expires_in || 900 // Default to 15 minutes if not provided
    };
    
    this.saveTokensToStorage(tokensWithExpiry);
    return tokens;
  }

  async register(userData: RegisterRequest): Promise<RegisterResponse> {
    const response = await this.request<RegisterResponse>('/register/', {
      method: 'POST',
      body: JSON.stringify(userData),
    }, true);
    
    // Save tokens from registration response
    this.saveTokensToStorage({
      access_token: response.access_token,
      refresh_token: response.refresh_token
    });
    
    return response;
  }

  async logout(): Promise<void> {
    try {
      await this.request('/logout/', { method: 'POST' }, true);
    } finally {
      this.clearTokensFromStorage();
    }
  }

  async refreshAccessToken(): Promise<boolean> {
    // Check if we're already refreshing to prevent multiple simultaneous refreshes
    if (this.isRefreshing && this.refreshPromise) {
      return this.refreshPromise;
    }
    
    // Check if we've hit max refresh attempts
    if (!this.refreshToken || this.refreshAttempts >= this.maxRefreshAttempts) {
      console.log(`Max refresh attempts reached (${this.refreshAttempts}/${this.maxRefreshAttempts}) or no refresh token`);
      this.clearTokensFromStorage();
      return false;
    }
    
    this.isRefreshing = true;
    this.refreshAttempts++;
    
    // Create refresh promise that other requests can await
    this.refreshPromise = new Promise<boolean>(async (resolve) => {
      try {
        console.log(`Attempting token refresh (attempt ${this.refreshAttempts}/${this.maxRefreshAttempts})...`);
        
        // Make refresh request directly without going through request() to avoid loops
        const response = await fetch(`${this.authURL}/refresh/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        });
        
        if (response.ok) {
          const data = await response.json() as { access_token: string; expires_in?: number };
          
          // Update tokens with the refreshed access token
          // Backend only returns new access_token, not refresh_token
          this.saveTokensToStorage({
            access_token: data.access_token,
            refresh_token: this.refreshToken!, // Keep existing refresh token
            expires_in: data.expires_in
          });
          
          console.log('Token refresh successful');
          this.isRefreshing = false;
          this.refreshPromise = null;
          resolve(true);
        } else {
          const errorData = await response.json().catch(() => ({}));
          console.error('Token refresh failed:', response.status, errorData);
          
          if (this.refreshAttempts >= this.maxRefreshAttempts) {
            console.log('Max refresh attempts reached, clearing tokens');
            this.clearTokensFromStorage();
          }
          
          this.isRefreshing = false;
          this.refreshPromise = null;
          resolve(false);
        }
      } catch (error) {
        console.error('Token refresh error:', error);
        
        if (this.refreshAttempts >= this.maxRefreshAttempts) {
          this.clearTokensFromStorage();
        }
        
        this.isRefreshing = false;
        this.refreshPromise = null;
        resolve(false);
      }
    });
    
    return this.refreshPromise;
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/me/', {}, true);
  }

  // Chatbot methods
  async getChatbots(): Promise<Chatbot[]> {
    return this.request<Chatbot[]>('/chatbots/');
  }

  async getChatbot(id: string): Promise<Chatbot> {
    return this.request<Chatbot>(`/chatbots/${id}/`);
  }

  async createChatbot(data: Partial<Chatbot>): Promise<Chatbot> {
    return this.request<Chatbot>('/chatbots/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateChatbot(id: string, data: Partial<Chatbot>): Promise<Chatbot> {
    return this.request<Chatbot>(`/chatbots/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async deleteChatbot(id: string): Promise<void> {
    await this.request(`/chatbots/${id}/`, { method: 'DELETE' });
  }

  async getChatbotSettings(id: string): Promise<any> {
    return this.request<any>(`/chatbots/${id}/get_settings/`);
  }

  async updateChatbotSettings(id: string, data: { system_prompt?: string; response_guidelines?: string }): Promise<any> {
    return this.request<any>(`/chatbots/${id}/update_settings/`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Conversation methods
  async getConversations(chatbotId?: string): Promise<Conversation[]> {
    const params = chatbotId ? `?chatbot=${chatbotId}` : '';
    return this.request<Conversation[]>(`/conversations/${params}`);
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${id}/`);
  }

  async getConversationMessages(conversationId: string): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages/`);
  }

  // Chat methods (REST API for initial message)
  async sendPrivateMessage(
    chatbotId: string,
    message: ChatMessage
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>(`/chat/private/${chatbotId}/`, {
      method: 'POST',
      body: JSON.stringify(message),
    });
  }

  async sendPublicMessage(
    slug: string,
    message: ChatMessage
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>(`/chat/public/${slug}/`, {
      method: 'POST',
      body: JSON.stringify(message),
    });
  }

  // Widget configuration for public chatbots
  async getWidgetConfig(slug: string): Promise<any> {
    return this.request<any>(`/chat/public/${slug}/config/`);
  }

  // Analytics methods
  async getConversationAnalytics(params?: {
    date_from?: string;
    date_to?: string;
  }): Promise<any> {
    const searchParams = new URLSearchParams(params).toString();
    const endpoint = `/conversations/analytics/${searchParams ? `?${searchParams}` : ''}`;
    return this.request<any>(endpoint);
  }

  // Chat methods - MISSING METHOD ADDED FOR RAG INTEGRATION
  async sendChatMessage(
    chatbotId: string,
    message: { message: string; conversation_id?: string }
  ): Promise<{ response: string; conversation_id?: string; sources?: string[] }> {
    // Call the private chat endpoint which connects to the working RAG pipeline
    const response = await this.request<any>(`/chat/private/${chatbotId}/`, {
      method: 'POST',
      body: JSON.stringify(message),
    });
    
    // Map RAG response to expected frontend format
    return {
      response: response.message || response.content || 'No response generated',
      conversation_id: response.conversation_id,
      sources: response.citations || response.sources || []
    };
  }

  // Generic GET method
  async get<T>(endpoint: string, useAuthURL = false): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' }, useAuthURL);
  }

  // Knowledge file upload method - STEP 1 FIX: Frontend API disconnect
  async uploadKnowledgeFile(
    chatbotId: string,
    file: File,
    options?: {
      name?: string;
      description?: string;
      is_citable?: boolean;
    }
  ): Promise<any> {
    // Create FormData for multipart file upload
    const formData = new FormData();
    formData.append('file', file);
    formData.append('chatbot_id', chatbotId);
    
    if (options?.name) {
      formData.append('name', options.name);
    }
    if (options?.description) {
      formData.append('description', options.description);
    }
    if (options?.is_citable !== undefined) {
      formData.append('is_citable', options.is_citable.toString());
    }

    // Make request without JSON content-type for multipart upload
    const url = `${this.baseURL}/knowledge/upload/document/`;
    
    const headers: Record<string, string> = {};
    if (this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }
    // Don't set Content-Type - let browser set it with boundary for multipart

    try {
      // Check if token needs refresh before making request
      if (this.accessToken) {
        await this.ensureValidToken();
      }

      let response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData,
      });

      // Handle token refresh on 401
      if (response.status === 401 && this.refreshToken) {
        console.log('Got 401 on file upload, attempting token refresh...');
        const refreshed = await this.refreshAccessToken();
        
        if (refreshed) {
          // Retry with new token
          headers.Authorization = `Bearer ${this.accessToken}`;
          response = await fetch(url, {
            method: 'POST',
            headers,
            body: formData,
          });
        } else {
          console.log('Token refresh failed, redirecting to login...');
          window.location.href = '/login';
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        let errorMessage = `HTTP Error ${response.status}`;
        if (errorData.error) {
          errorMessage = errorData.error;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        }
        
        throw new ApiError(errorMessage, response.status, errorData);
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('File upload failed', 0, error);
    }
  }

  // Knowledge URL processing method - STEP 1 FIX: Frontend API disconnect  
  async addKnowledgeUrl(
    chatbotId: string,
    urlData: {
      url: string;
      name?: string;
      description?: string;
      is_citable?: boolean;
    }
  ): Promise<any> {
    return this.request<any>('/knowledge/upload/url/', {
      method: 'POST',
      body: JSON.stringify({
        chatbot_id: chatbotId,
        url: urlData.url,
        name: urlData.name || urlData.url,
        description: urlData.description || '',
        is_citable: urlData.is_citable !== undefined ? urlData.is_citable : true
      }),
    });
  }

  // Utility methods
  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }
}

export const apiService = new ApiService();
export { ApiError };