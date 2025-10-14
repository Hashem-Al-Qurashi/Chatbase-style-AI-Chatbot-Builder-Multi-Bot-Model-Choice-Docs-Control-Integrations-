/**
 * Embeddable Chatbot Widget
 * A standalone vanilla JavaScript widget that can be embedded in any website
 * Connects to the chatbot SaaS backend via REST API and WebSocket
 */

(function() {
  'use strict';

  // Widget configuration
  const CONFIG = {
    apiBaseUrl: window.CHATBOT_API_URL || window.location.origin + '/api/v1',
    wsBaseUrl: window.CHATBOT_WS_URL || (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host,
    defaultTheme: {
      primaryColor: '#007bff',
      backgroundColor: '#ffffff',
      textColor: '#333333',
      borderRadius: '8px',
      fontFamily: 'Arial, sans-serif'
    }
  };

  // Main ChatbotWidget class
  class ChatbotWidget {
    constructor(options = {}) {
      this.options = {
        chatbotSlug: options.chatbotSlug || '',
        theme: { ...CONFIG.defaultTheme, ...options.theme },
        position: options.position || 'bottom-right',
        triggerText: options.triggerText || 'Chat with us',
        welcomeMessage: options.welcomeMessage || 'Hi! How can I help you today?',
        height: options.height || '500px',
        width: options.width || '350px',
        ...options
      };

      this.isOpen = false;
      this.messages = [];
      this.sessionId = null;
      this.websocket = null;
      this.isTyping = false;
      this.reconnectAttempts = 0;
      this.maxReconnectAttempts = 3;

      this.init();
    }

    init() {
      this.loadConfig()
        .then(() => {
          this.createWidget();
          this.bindEvents();
          this.addStyles();
        })
        .catch(error => {
          console.error('Failed to initialize chatbot widget:', error);
        });
    }

    async loadConfig() {
      if (!this.options.chatbotSlug) {
        throw new Error('Chatbot slug is required');
      }

      try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/chat/public/${this.options.chatbotSlug}/config/`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        this.config = await response.json();
        
        // Apply any config-based customizations
        if (this.config.settings?.custom_css) {
          this.options.customCSS = this.config.settings.custom_css;
        }
      } catch (error) {
        console.error('Failed to load chatbot config:', error);
        throw error;
      }
    }

    createWidget() {
      // Create main container
      this.container = document.createElement('div');
      this.container.id = 'chatbot-widget-container';
      this.container.innerHTML = `
        <!-- Trigger Button -->
        <div id="chatbot-trigger" class="chatbot-trigger chatbot-trigger-${this.options.position}">
          <span id="chatbot-trigger-text">${this.options.triggerText}</span>
          <span id="chatbot-trigger-close" style="display: none;">×</span>
        </div>

        <!-- Chat Window -->
        <div id="chatbot-window" class="chatbot-window chatbot-window-${this.options.position}" style="display: none;">
          <!-- Header -->
          <div class="chatbot-header">
            <div class="chatbot-title">
              <h4>${this.config.name || 'Chatbot'}</h4>
              <div class="chatbot-status">
                <span id="chatbot-status-indicator" class="status-indicator offline"></span>
                <span id="chatbot-status-text">Connecting...</span>
              </div>
            </div>
            <button id="chatbot-close" class="chatbot-close">×</button>
          </div>

          <!-- Messages Area -->
          <div id="chatbot-messages" class="chatbot-messages">
            <div class="chatbot-message chatbot-message-bot">
              <div class="message-content">${this.options.welcomeMessage}</div>
              <div class="message-time">${this.formatTime(new Date())}</div>
            </div>
          </div>

          <!-- Typing Indicator -->
          <div id="chatbot-typing" class="chatbot-typing" style="display: none;">
            <span class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </span>
            <span class="typing-text">AI is typing...</span>
          </div>

          <!-- Input Area -->
          <div class="chatbot-input-area">
            <div class="chatbot-input-container">
              <input 
                type="text" 
                id="chatbot-input" 
                placeholder="Type your message..."
                maxlength="500"
              />
              <button id="chatbot-send" class="chatbot-send-button" disabled>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Footer -->
          ${this.config.settings?.show_powered_by !== false ? `
            <div class="chatbot-footer">
              <small>Powered by <a href="#" target="_blank">Chatbot SaaS</a></small>
            </div>
          ` : ''}
        </div>
      `;

      document.body.appendChild(this.container);
    }

    addStyles() {
      const style = document.createElement('style');
      style.textContent = `
        /* Chatbot Widget Styles */
        #chatbot-widget-container {
          position: fixed;
          z-index: 999999;
          font-family: ${this.options.theme.fontFamily};
        }

        .chatbot-trigger {
          position: fixed;
          background: ${this.options.theme.primaryColor};
          color: white;
          padding: 12px 20px;
          border-radius: 25px;
          cursor: pointer;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          transition: all 0.3s ease;
          font-size: 14px;
          font-weight: 500;
          user-select: none;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .chatbot-trigger:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(0,0,0,0.2);
        }

        .chatbot-trigger-bottom-right {
          bottom: 20px;
          right: 20px;
        }

        .chatbot-trigger-bottom-left {
          bottom: 20px;
          left: 20px;
        }

        .chatbot-window {
          position: fixed;
          width: ${this.options.width};
          height: ${this.options.height};
          background: ${this.options.theme.backgroundColor};
          border-radius: ${this.options.theme.borderRadius};
          box-shadow: 0 8px 32px rgba(0,0,0,0.1);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          border: 1px solid #e1e8ed;
        }

        .chatbot-window-bottom-right {
          bottom: 80px;
          right: 20px;
        }

        .chatbot-window-bottom-left {
          bottom: 80px;
          left: 20px;
        }

        .chatbot-header {
          background: ${this.options.theme.primaryColor};
          color: white;
          padding: 15px;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .chatbot-title h4 {
          margin: 0;
          font-size: 16px;
          font-weight: 600;
        }

        .chatbot-status {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          opacity: 0.9;
          margin-top: 2px;
        }

        .status-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #dc3545;
        }

        .status-indicator.online {
          background: #28a745;
        }

        .chatbot-close {
          background: none;
          border: none;
          color: white;
          font-size: 20px;
          cursor: pointer;
          padding: 0;
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          transition: background-color 0.2s;
        }

        .chatbot-close:hover {
          background: rgba(255,255,255,0.1);
        }

        .chatbot-messages {
          flex: 1;
          overflow-y: auto;
          padding: 15px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .chatbot-message {
          display: flex;
          flex-direction: column;
          max-width: 80%;
        }

        .chatbot-message-user {
          align-self: flex-end;
          align-items: flex-end;
        }

        .chatbot-message-bot {
          align-self: flex-start;
          align-items: flex-start;
        }

        .message-content {
          padding: 10px 14px;
          border-radius: 18px;
          font-size: 14px;
          line-height: 1.4;
          word-wrap: break-word;
        }

        .chatbot-message-user .message-content {
          background: ${this.options.theme.primaryColor};
          color: white;
        }

        .chatbot-message-bot .message-content {
          background: #f1f3f4;
          color: ${this.options.theme.textColor};
        }

        .message-time {
          font-size: 11px;
          color: #8e8e93;
          margin-top: 4px;
          padding: 0 8px;
        }

        .chatbot-typing {
          padding: 15px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: #8e8e93;
        }

        .typing-dots {
          display: flex;
          gap: 2px;
        }

        .typing-dots span {
          width: 4px;
          height: 4px;
          border-radius: 50%;
          background: #8e8e93;
          animation: typing 1.4s infinite ease-in-out;
        }

        .typing-dots span:nth-child(1) { animation-delay: -0.32s; }
        .typing-dots span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes typing {
          0%, 80%, 100% { opacity: 0.3; }
          40% { opacity: 1; }
        }

        .chatbot-input-area {
          border-top: 1px solid #e1e8ed;
          padding: 15px;
        }

        .chatbot-input-container {
          display: flex;
          gap: 8px;
          align-items: center;
        }

        #chatbot-input {
          flex: 1;
          border: 1px solid #e1e8ed;
          border-radius: 20px;
          padding: 10px 15px;
          font-size: 14px;
          outline: none;
          transition: border-color 0.2s;
        }

        #chatbot-input:focus {
          border-color: ${this.options.theme.primaryColor};
        }

        .chatbot-send-button {
          background: ${this.options.theme.primaryColor};
          border: none;
          color: white;
          width: 36px;
          height: 36px;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s;
        }

        .chatbot-send-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .chatbot-send-button:not(:disabled):hover {
          transform: scale(1.05);
        }

        .chatbot-footer {
          padding: 8px 15px;
          text-align: center;
          border-top: 1px solid #e1e8ed;
          background: #fafbfc;
        }

        .chatbot-footer a {
          color: ${this.options.theme.primaryColor};
          text-decoration: none;
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .chatbot-window {
            width: calc(100vw - 20px);
            height: calc(100vh - 100px);
            max-width: none;
          }

          .chatbot-window-bottom-right,
          .chatbot-window-bottom-left {
            bottom: 80px;
            left: 10px;
            right: 10px;
          }
        }

        /* Custom CSS */
        ${this.options.customCSS || ''}
      `;

      document.head.appendChild(style);
    }

    bindEvents() {
      const trigger = document.getElementById('chatbot-trigger');
      const window = document.getElementById('chatbot-window');
      const closeBtn = document.getElementById('chatbot-close');
      const input = document.getElementById('chatbot-input');
      const sendBtn = document.getElementById('chatbot-send');

      trigger.addEventListener('click', () => this.toggleWidget());
      closeBtn.addEventListener('click', () => this.closeWidget());
      
      input.addEventListener('input', (e) => {
        sendBtn.disabled = !e.target.value.trim();
        this.sendTypingIndicator(!!e.target.value.trim());
      });

      input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this.sendMessage();
        }
      });

      sendBtn.addEventListener('click', () => this.sendMessage());

      // Auto-resize for mobile
      window.addEventListener('resize', () => this.handleResize());
    }

    toggleWidget() {
      if (this.isOpen) {
        this.closeWidget();
      } else {
        this.openWidget();
      }
    }

    openWidget() {
      const window = document.getElementById('chatbot-window');
      const triggerText = document.getElementById('chatbot-trigger-text');
      const triggerClose = document.getElementById('chatbot-trigger-close');

      window.style.display = 'flex';
      triggerText.style.display = 'none';
      triggerClose.style.display = 'block';
      
      this.isOpen = true;
      
      // Initialize WebSocket connection
      this.connectWebSocket();
      
      // Focus input
      setTimeout(() => {
        document.getElementById('chatbot-input').focus();
      }, 100);
    }

    closeWidget() {
      const window = document.getElementById('chatbot-window');
      const triggerText = document.getElementById('chatbot-trigger-text');
      const triggerClose = document.getElementById('chatbot-trigger-close');

      window.style.display = 'none';
      triggerText.style.display = 'block';
      triggerClose.style.display = 'none';
      
      this.isOpen = false;
      
      // Disconnect WebSocket
      this.disconnectWebSocket();
    }

    async connectWebSocket() {
      try {
        const wsUrl = `${CONFIG.wsBaseUrl}/ws/chat/public/${this.options.chatbotSlug}/`;
        this.websocket = new WebSocket(wsUrl);

        this.websocket.onopen = () => {
          console.log('WebSocket connected');
          this.updateConnectionStatus(true);
          this.reconnectAttempts = 0;
        };

        this.websocket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleWebSocketMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.websocket.onclose = () => {
          console.log('WebSocket disconnected');
          this.updateConnectionStatus(false);
          
          // Attempt reconnection
          if (this.isOpen && this.reconnectAttempts < this.maxReconnectAttempts) {
            setTimeout(() => {
              this.reconnectAttempts++;
              this.connectWebSocket();
            }, 2000 * this.reconnectAttempts);
          }
        };

        this.websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.updateConnectionStatus(false);
        };

      } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        this.updateConnectionStatus(false);
      }
    }

    disconnectWebSocket() {
      if (this.websocket) {
        this.websocket.close();
        this.websocket = null;
      }
    }

    handleWebSocketMessage(message) {
      switch (message.type) {
        case 'connection_established':
          this.sessionId = message.conversation_id;
          this.updateConnectionStatus(true);
          break;
          
        case 'chat_message':
          if (message.role === 'assistant') {
            this.hideTypingIndicator();
            this.addMessage(message.content, 'bot', message.citations);
          }
          break;
          
        case 'typing_indicator':
          if (message.is_typing) {
            this.showTypingIndicator();
          } else {
            this.hideTypingIndicator();
          }
          break;
          
        case 'error':
          console.error('WebSocket error:', message.message);
          this.showError(message.message);
          break;
      }
    }

    updateConnectionStatus(isConnected) {
      const indicator = document.getElementById('chatbot-status-indicator');
      const text = document.getElementById('chatbot-status-text');
      
      if (isConnected) {
        indicator.className = 'status-indicator online';
        text.textContent = 'Online';
      } else {
        indicator.className = 'status-indicator offline';
        text.textContent = 'Connecting...';
      }
    }

    sendMessage() {
      const input = document.getElementById('chatbot-input');
      const message = input.value.trim();
      
      if (!message || !this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
        return;
      }

      // Add user message to UI
      this.addMessage(message, 'user');
      
      // Send via WebSocket
      this.websocket.send(JSON.stringify({
        type: 'chat_message',
        message: message,
        session_id: this.sessionId
      }));

      // Clear input
      input.value = '';
      document.getElementById('chatbot-send').disabled = true;
    }

    sendTypingIndicator(isTyping) {
      if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
        this.websocket.send(JSON.stringify({
          type: 'typing_indicator',
          is_typing: isTyping
        }));
      }
    }

    addMessage(content, sender, citations = null) {
      const messagesContainer = document.getElementById('chatbot-messages');
      const messageEl = document.createElement('div');
      messageEl.className = `chatbot-message chatbot-message-${sender}`;
      
      let citationsHtml = '';
      if (citations && citations.length > 0) {
        citationsHtml = `
          <div class="message-citations">
            <small>Sources: ${citations.join(', ')}</small>
          </div>
        `;
      }

      messageEl.innerHTML = `
        <div class="message-content">${this.escapeHtml(content)}</div>
        ${citationsHtml}
        <div class="message-time">${this.formatTime(new Date())}</div>
      `;

      messagesContainer.appendChild(messageEl);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      // Store message
      this.messages.push({ content, sender, timestamp: new Date(), citations });
    }

    showTypingIndicator() {
      document.getElementById('chatbot-typing').style.display = 'flex';
      this.isTyping = true;
    }

    hideTypingIndicator() {
      document.getElementById('chatbot-typing').style.display = 'none';
      this.isTyping = false;
    }

    showError(message) {
      this.addMessage(`Error: ${message}`, 'bot');
    }

    formatTime(date) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    }

    handleResize() {
      // Handle mobile responsive behavior
      if (window.innerWidth <= 768) {
        const chatWindow = document.getElementById('chatbot-window');
        if (chatWindow) {
          chatWindow.style.width = 'calc(100vw - 20px)';
          chatWindow.style.height = 'calc(100vh - 100px)';
        }
      }
    }
  }

  // Auto-initialization from script tag attributes
  function autoInit() {
    const scripts = document.getElementsByTagName('script');
    let widgetScript = null;
    
    for (let script of scripts) {
      if (script.src && script.src.includes('chatbot-widget.js')) {
        widgetScript = script;
        break;
      }
    }

    if (widgetScript) {
      const options = {
        chatbotSlug: widgetScript.getAttribute('data-chatbot-slug'),
        theme: {
          primaryColor: widgetScript.getAttribute('data-primary-color'),
          backgroundColor: widgetScript.getAttribute('data-background-color'),
          textColor: widgetScript.getAttribute('data-text-color'),
        },
        position: widgetScript.getAttribute('data-position'),
        triggerText: widgetScript.getAttribute('data-trigger-text'),
        welcomeMessage: widgetScript.getAttribute('data-welcome-message'),
        height: widgetScript.getAttribute('data-height'),
        width: widgetScript.getAttribute('data-width'),
      };

      // Remove undefined values
      Object.keys(options).forEach(key => {
        if (options[key] === null || options[key] === undefined) {
          delete options[key];
        }
      });

      // Remove empty theme properties
      Object.keys(options.theme).forEach(key => {
        if (options.theme[key] === null || options.theme[key] === undefined) {
          delete options.theme[key];
        }
      });

      if (options.chatbotSlug) {
        new ChatbotWidget(options);
      }
    }
  }

  // Export for manual initialization
  window.ChatbotWidget = ChatbotWidget;

  // Auto-initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

})();