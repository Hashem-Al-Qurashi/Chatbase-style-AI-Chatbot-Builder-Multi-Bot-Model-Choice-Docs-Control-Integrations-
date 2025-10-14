# Chatbot Widget Integration Guide

## Overview

The Chatbot Widget is a standalone, embeddable JavaScript component that provides real-time AI-powered chat functionality for any website. Built with vanilla JavaScript and WebSocket technology, it offers seamless integration without external dependencies.

## Features

- 🚀 **Easy Integration** - Single script tag setup
- 📱 **Mobile Responsive** - Automatically adapts to all screen sizes
- ⚡ **Real-time Chat** - WebSocket-powered live messaging
- 🎨 **Fully Customizable** - Extensive theming and positioning options
- 🤖 **AI-Powered** - RAG-based intelligent responses with source citations
- 📊 **Analytics Ready** - Conversation tracking and lead capture
- 🔒 **Secure** - CORS-compliant with rate limiting
- ♿ **Accessible** - WCAG compliance with keyboard navigation

## Quick Start

### Simple Integration

Add this single script tag to your HTML:

```html
<script 
    src="https://your-domain.com/widget/chatbot-widget.js"
    data-chatbot-slug="your-chatbot-slug"
    data-primary-color="#007bff"
    data-trigger-text="Chat with us"
></script>
```

### Required Parameters

- `data-chatbot-slug`: Your unique chatbot identifier (obtain from dashboard)

### Optional Customization

| Attribute | Default | Description |
|-----------|---------|-------------|
| `data-primary-color` | `#007bff` | Main theme color |
| `data-background-color` | `#ffffff` | Widget background |
| `data-text-color` | `#333333` | Text color |
| `data-position` | `bottom-right` | Widget position (`bottom-right`, `bottom-left`) |
| `data-trigger-text` | `Chat with us` | Trigger button text |
| `data-welcome-message` | `Hi! How can I help you today?` | Initial message |
| `data-height` | `500px` | Widget height |
| `data-width` | `350px` | Widget width |

## Advanced Integration

### Programmatic Initialization

```html
<script src="https://your-domain.com/widget/chatbot-widget.js"></script>
<script>
const widget = new ChatbotWidget({
    chatbotSlug: 'your-chatbot-slug',
    theme: {
        primaryColor: '#6f42c1',
        backgroundColor: '#ffffff',
        textColor: '#333333',
        borderRadius: '12px',
        fontFamily: 'Inter, sans-serif'
    },
    position: 'bottom-left',
    triggerText: 'Need Help?',
    welcomeMessage: 'Welcome! How can I assist you today?',
    height: '600px',
    width: '400px',
    customCSS: `
        .chatbot-window {
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        .chatbot-header {
            background: linear-gradient(45deg, #667eea, #764ba2);
        }
    `
});
</script>
```

### Custom Theme Configuration

```javascript
const customTheme = {
    primaryColor: '#ff6b6b',           // Brand color
    backgroundColor: '#ffffff',        // Widget background
    textColor: '#2c3e50',             // Text color
    borderRadius: '16px',             // Corner radius
    fontFamily: 'system-ui, sans-serif' // Font family
};

new ChatbotWidget({
    chatbotSlug: 'your-slug',
    theme: customTheme
});
```

## Responsive Design

The widget automatically adapts to different screen sizes:

- **Desktop**: Fixed size widget with customizable dimensions
- **Tablet**: Responsive sizing with touch-optimized controls
- **Mobile**: Full-screen overlay with mobile-optimized layout

## Browser Support

- ✅ Chrome 60+
- ✅ Firefox 55+
- ✅ Safari 12+
- ✅ Edge 79+
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

## Security & Performance

### Security Features
- CORS-compliant requests
- Rate limiting protection
- Input sanitization
- Secure WebSocket connections (WSS in production)

### Performance Optimizations
- Minimal bundle size (~15KB gzipped)
- Lazy loading of resources
- Efficient WebSocket connection management
- Optimized for Core Web Vitals

## API Integration

The widget communicates with your chatbot backend through:

### REST API Endpoints
- `GET /api/v1/chat/public/{slug}/config/` - Widget configuration
- `POST /api/v1/chat/public/{slug}/` - Send chat messages
- `POST /api/v1/chat/public/{slug}/lead/` - Capture leads

### WebSocket Connection
- `ws://your-domain/ws/chat/public/{slug}/` - Real-time chat

## Customization Examples

### E-commerce Theme
```html
<script 
    src="./chatbot-widget.js"
    data-chatbot-slug="shop-assistant"
    data-primary-color="#28a745"
    data-trigger-text="🛍️ Shopping Help"
    data-welcome-message="Hi! Need help finding the perfect product?"
    data-position="bottom-right"
></script>
```

### Support Theme
```html
<script 
    src="./chatbot-widget.js"
    data-chatbot-slug="support-bot"
    data-primary-color="#dc3545"
    data-trigger-text="🆘 Get Support"
    data-welcome-message="I'm here to help resolve any issues you're having."
    data-position="bottom-left"
></script>
```

### Professional Services Theme
```html
<script 
    src="./chatbot-widget.js"
    data-chatbot-slug="consulting-ai"
    data-primary-color="#6f42c1"
    data-trigger-text="💼 Free Consultation"
    data-welcome-message="Schedule a consultation or ask about our services."
    data-height="650px"
    data-width="420px"
></script>
```

## Troubleshooting

### Common Issues

**Widget not appearing:**
- Verify the script URL is correct
- Check that `data-chatbot-slug` matches your chatbot
- Ensure the chatbot is published and active

**Connection issues:**
- Check browser console for WebSocket errors
- Verify CORS settings allow your domain
- Ensure WebSocket URL is accessible

**Styling conflicts:**
- Use CSS specificity or `!important` for custom styles
- Check for conflicting CSS frameworks
- Utilize the `customCSS` option for targeted styling

### Debug Mode

Enable debug logging:

```javascript
window.CHATBOT_DEBUG = true;
```

### Browser Console

Monitor the browser console for:
- WebSocket connection status
- API request/response logs
- Error messages and stack traces

## Lead Capture

The widget supports automatic lead capture:

```javascript
// Triggered automatically based on conversation flow
// Or manually via your chatbot configuration
```

Captured leads include:
- Email address
- Name (optional)
- Phone number (optional)
- Conversation context
- Timestamp

## Analytics Integration

Track widget performance:

```javascript
// Widget events (when implemented)
widget.on('open', () => console.log('Widget opened'));
widget.on('message', (data) => console.log('Message sent:', data));
widget.on('lead', (data) => console.log('Lead captured:', data));
```

## Best Practices

### Performance
1. Load the widget script asynchronously when possible
2. Use appropriate `data-height` and `data-width` for your layout
3. Minimize custom CSS complexity
4. Test on various devices and network conditions

### User Experience
1. Choose appropriate trigger text for your audience
2. Position the widget where it's visible but not intrusive
3. Use brand-consistent colors and messaging
4. Test the conversation flow thoroughly

### SEO & Accessibility
1. The widget doesn't impact SEO as it loads asynchronously
2. Include `aria-label` attributes for screen readers
3. Ensure sufficient color contrast (4.5:1 ratio minimum)
4. Test keyboard navigation functionality

## Support

For implementation support:
- Check the example.html file for working examples
- Review browser console for error messages
- Verify your chatbot configuration in the dashboard
- Test with different browsers and devices

## Changelog

### Version 1.0.0
- Initial release with core functionality
- WebSocket real-time communication
- Mobile responsive design
- Customizable theming
- Lead capture integration
- Accessibility features