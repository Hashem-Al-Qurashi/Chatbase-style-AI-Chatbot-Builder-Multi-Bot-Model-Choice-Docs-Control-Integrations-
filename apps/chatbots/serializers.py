"""
Serializers for chatbots app.
Handles chatbot configuration, customization, and analytics.
"""

import re
import bleach
from rest_framework import serializers
from apps.chatbots.models import Chatbot, ChatbotSettings, ChatbotAnalytics


class ChatbotSerializer(serializers.ModelSerializer):
    """Main chatbot serializer."""
    
    public_url = serializers.SerializerMethodField()
    embed_url = serializers.SerializerMethodField()
    embed_script = serializers.SerializerMethodField()
    is_ready = serializers.SerializerMethodField()
    has_knowledge_sources = serializers.SerializerMethodField()
    
    class Meta:
        model = Chatbot
        fields = (
            'id', 'name', 'description', 'public_url_slug',
            'theme_color', 'welcome_message', 'placeholder_text',
            'temperature', 'max_tokens', 'model_name',
            'enable_citations', 'enable_data_collection',
            'crm_webhook_url', 'status', 'last_trained_at',
            'total_conversations', 'total_messages',
            'public_url', 'embed_url', 'embed_script',
            'is_ready', 'has_knowledge_sources',
            'created_at', 'updated_at', 'metadata'
        )
        read_only_fields = (
            'id', 'public_url_slug', 'status', 'last_trained_at',
            'total_conversations', 'total_messages',
            'created_at', 'updated_at'
        )
        extra_kwargs = {
            'crm_webhook_url': {'write_only': True},
        }
    
    def get_public_url(self, obj):
        """Get public URL."""
        return obj.public_url
    
    def get_embed_url(self, obj):
        """Get embed URL."""
        return obj.embed_url
    
    def get_embed_script(self, obj):
        """Get embed script."""
        return obj.embed_script
    
    def get_is_ready(self, obj):
        """Check if chatbot is ready."""
        return obj.is_ready
    
    def get_has_knowledge_sources(self, obj):
        """Check if chatbot has knowledge sources."""
        return obj.has_knowledge_sources
    
    def _sanitize_text(self, value):
        """
        Comprehensive text sanitization to prevent XSS attacks.
        Removes HTML tags and their content completely.
        """
        if not value:
            return value
        
        # First, remove HTML tags with bleach (strip=True removes tags but keeps content)
        text = bleach.clean(value, tags=[], attributes={}, strip=True)
        
        # Remove any remaining HTML entities
        text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
        
        # Remove any javascript: or data: protocol attempts
        text = re.sub(r'(?i)javascript\s*:', '', text)
        text = re.sub(r'(?i)data\s*:', '', text)
        text = re.sub(r'(?i)vbscript\s*:', '', text)
        
        # Remove event handler attributes (comprehensive list)
        event_handlers = [
            'onload', 'onerror', 'onclick', 'onmouseover', 'onmouseout', 
            'onkeydown', 'onkeyup', 'onkeypress', 'onchange', 'onsubmit',
            'onfocus', 'onblur', 'onselect', 'onreset', 'onabort',
            'onunload', 'onresize', 'onscroll', 'ondblclick'
        ]
        for handler in event_handlers:
            text = re.sub(rf'(?i){handler}\s*=\s*[^"\s]*', '', text)
            text = re.sub(rf'(?i){handler}\s*=', '', text)
        
        # Remove any remaining angle brackets that could be used for injection
        text = re.sub(r'[<>]', '', text)
        
        # Remove any quotes that could break out of attributes
        text = re.sub(r'["\']', '', text)
        
        # Remove any equals signs that could be part of attribute injection
        text = re.sub(r'=', '', text)
        
        return text.strip()

    def validate_name(self, value):
        """Sanitize chatbot name to prevent XSS attacks."""
        if not value:
            raise serializers.ValidationError("Name cannot be empty")
        
        # Sanitize the input
        sanitized = self._sanitize_text(value)
        
        if not sanitized:
            raise serializers.ValidationError("Name cannot contain only HTML tags or invalid characters")
        
        if len(sanitized) > 255:
            raise serializers.ValidationError("Name cannot exceed 255 characters")
            
        return sanitized
    
    def validate_description(self, value):
        """Sanitize chatbot description to prevent XSS attacks."""
        if not value:
            return value
        
        # Sanitize the input
        sanitized = self._sanitize_text(value)
        
        if len(sanitized) > 1000:
            raise serializers.ValidationError("Description cannot exceed 1000 characters")
            
        return sanitized

    def create(self, validated_data):
        """Create chatbot with user from context."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatbotListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for chatbot lists."""
    
    is_ready = serializers.SerializerMethodField()
    
    class Meta:
        model = Chatbot
        fields = (
            'id', 'name', 'description', 'public_url_slug',
            'status', 'is_ready', 'total_conversations',
            'total_messages', 'created_at'
        )
        read_only_fields = fields
    
    def get_is_ready(self, obj):
        """Check if chatbot is ready."""
        return obj.is_ready


class ChatbotSettingsSerializer(serializers.ModelSerializer):
    """Chatbot settings serializer."""
    
    class Meta:
        model = ChatbotSettings
        fields = (
            'id', 'system_prompt', 'response_guidelines',
            'rate_limit_messages_per_hour', 'rate_limit_messages_per_day',
            'enable_profanity_filter', 'enable_spam_detection',
            'blocked_words', 'enable_sentiment_analysis',
            'enable_topic_extraction', 'enable_lead_capture',
            'lead_capture_trigger', 'lead_capture_message',
            'show_powered_by', 'custom_css'
        )
        read_only_fields = ('id',)


class ChatbotAnalyticsSerializer(serializers.ModelSerializer):
    """Chatbot analytics serializer."""
    
    chatbot_name = serializers.CharField(source='chatbot.name', read_only=True)
    
    class Meta:
        model = ChatbotAnalytics
        fields = (
            'id', 'chatbot', 'chatbot_name', 'date', 'hour',
            'unique_visitors', 'total_conversations', 'total_messages',
            'avg_conversation_length', 'avg_response_time',
            'bounce_rate', 'user_satisfaction', 'leads_captured',
            'conversion_rate', 'top_queries', 'top_sources_cited'
        )
        read_only_fields = fields


class ChatbotTrainingSerializer(serializers.Serializer):
    """Serializer for chatbot training requests."""
    
    force_retrain = serializers.BooleanField(default=False)
    knowledge_source_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific knowledge sources to train on"
    )


class ChatbotTestSerializer(serializers.Serializer):
    """Serializer for testing chatbot responses."""
    
    message = serializers.CharField(required=True, max_length=2000)
    conversation_id = serializers.UUIDField(required=False)
    include_sources = serializers.BooleanField(default=True)
    
    
class ChatbotCloneSerializer(serializers.Serializer):
    """Serializer for cloning a chatbot."""
    
    name = serializers.CharField(required=True, max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    include_settings = serializers.BooleanField(default=True)
    include_knowledge = serializers.BooleanField(default=False)


class ChatbotExportSerializer(serializers.Serializer):
    """Serializer for exporting chatbot configuration."""
    
    include_settings = serializers.BooleanField(default=True)
    include_knowledge = serializers.BooleanField(default=True)
    include_analytics = serializers.BooleanField(default=False)
    format = serializers.ChoiceField(choices=['json', 'yaml'], default='json')


class ChatbotImportSerializer(serializers.Serializer):
    """Serializer for importing chatbot configuration."""
    
    config_file = serializers.FileField(required=True)
    overwrite = serializers.BooleanField(default=False)
    
    def validate_config_file(self, value):
        """Validate configuration file."""
        if value.size > 10 * 1024 * 1024:  # 10MB limit
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Validate file format
        if not value.name.endswith(('.json', '.yaml', '.yml')):
            raise serializers.ValidationError("File must be JSON or YAML format")
        
        return value


class PublicChatbotSerializer(serializers.ModelSerializer):
    """Public chatbot serializer (for embed/widget)."""
    
    class Meta:
        model = Chatbot
        fields = (
            'name', 'description', 'theme_color',
            'welcome_message', 'placeholder_text',
            'enable_citations', 'enable_data_collection'
        )
        read_only_fields = fields