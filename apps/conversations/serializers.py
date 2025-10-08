"""
Serializers for conversations app.
Handles chat conversations, messages, and lead capture.
"""

from rest_framework import serializers
from apps.conversations.models import (
    Conversation, Message, MessageSource, ConversationTag
)
from apps.knowledge.models import KnowledgeChunk


class MessageSourceSerializer(serializers.ModelSerializer):
    """Serializer for message sources/citations."""
    
    source_name = serializers.CharField(source='chunk.source.name', read_only=True)
    source_type = serializers.CharField(source='chunk.source.source_type', read_only=True)
    chunk_content = serializers.CharField(source='chunk.content', read_only=True)
    
    class Meta:
        model = MessageSource
        fields = (
            'id', 'chunk', 'source_name', 'source_type',
            'relevance_score', 'citation_text', 'chunk_content'
        )
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for conversation messages."""
    
    sources = MessageSourceSerializer(source='source_citations', many=True, read_only=True)
    
    class Meta:
        model = Message
        fields = (
            'id', 'role', 'content', 'sequence_number',
            'model_used', 'temperature', 'token_usage',
            'generation_time_ms', 'sources', 'is_helpful',
            'is_flagged', 'flag_reason', 'created_at', 'metadata'
        )
        read_only_fields = (
            'id', 'sequence_number', 'model_used', 'temperature',
            'token_usage', 'generation_time_ms', 'sources', 'created_at'
        )


class ConversationSerializer(serializers.ModelSerializer):
    """Full conversation serializer with messages."""
    
    messages = MessageSerializer(many=True, read_only=True)
    chatbot_name = serializers.CharField(source='chatbot.name', read_only=True)
    
    class Meta:
        model = Conversation
        fields = (
            'id', 'chatbot', 'chatbot_name', 'session_id',
            'title', 'language', 'message_count',
            'user_satisfaction', 'satisfaction_feedback',
            'is_active', 'ended_at', 'has_lead',
            'lead_email', 'lead_name', 'lead_phone',
            'lead_captured_at', 'messages',
            'created_at', 'updated_at', 'metadata'
        )
        read_only_fields = (
            'id', 'session_id', 'message_count', 'ended_at',
            'lead_captured_at', 'created_at', 'updated_at'
        )


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists."""
    
    chatbot_name = serializers.CharField(source='chatbot.name', read_only=True)
    has_lead = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = (
            'id', 'chatbot', 'chatbot_name', 'session_id',
            'title', 'message_count', 'user_satisfaction',
            'is_active', 'has_lead', 'duration_minutes',
            'created_at', 'updated_at'
        )
        read_only_fields = fields
    
    def get_has_lead(self, obj):
        """Check if conversation has lead."""
        return obj.has_lead
    
    def get_duration_minutes(self, obj):
        """Get conversation duration."""
        return obj.duration_minutes


class ConversationTagSerializer(serializers.ModelSerializer):
    """Serializer for conversation tags."""
    
    class Meta:
        model = ConversationTag
        fields = (
            'id', 'tag', 'confidence', 'is_auto_generated'
        )
        read_only_fields = ('id', 'confidence', 'is_auto_generated')


class ChatMessageSerializer(serializers.Serializer):
    """Serializer for chat messages (public endpoint)."""
    
    message = serializers.CharField(required=True, max_length=2000)
    session_id = serializers.UUIDField(required=False)
    language = serializers.CharField(required=False, default='en', max_length=10)
    
    def validate_message(self, value):
        """Validate message content."""
        if not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat responses (public endpoint)."""
    
    message = serializers.CharField()
    session_id = serializers.UUIDField()
    sources = serializers.ListField(
        child=serializers.DictField(),
        required=False
    )
    suggested_followups = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )


class LeadCaptureSerializer(serializers.Serializer):
    """Serializer for lead capture."""
    
    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=False, max_length=255)
    phone = serializers.CharField(required=False, max_length=20)
    conversation_id = serializers.UUIDField(required=False)
    session_id = serializers.UUIDField(required=False)
    
    def validate(self, attrs):
        """Validate either conversation_id or session_id is provided."""
        if not attrs.get('conversation_id') and not attrs.get('session_id'):
            raise serializers.ValidationError(
                "Either conversation_id or session_id must be provided"
            )
        return attrs


class ConversationFeedbackSerializer(serializers.Serializer):
    """Serializer for conversation feedback."""
    
    rating = serializers.FloatField(min_value=1, max_value=5, required=True)
    feedback = serializers.CharField(required=False, max_length=1000)
    conversation_id = serializers.UUIDField(required=False)
    session_id = serializers.UUIDField(required=False)
    
    def validate(self, attrs):
        """Validate either conversation_id or session_id is provided."""
        if not attrs.get('conversation_id') and not attrs.get('session_id'):
            raise serializers.ValidationError(
                "Either conversation_id or session_id must be provided"
            )
        return attrs


class MessageFeedbackSerializer(serializers.Serializer):
    """Serializer for message feedback."""
    
    message_id = serializers.UUIDField(required=True)
    is_helpful = serializers.BooleanField(required=False)
    flag = serializers.BooleanField(default=False)
    flag_reason = serializers.ChoiceField(
        choices=['inappropriate', 'incorrect', 'spam', 'other'],
        required=False
    )
    
    def validate(self, attrs):
        """Validate feedback type."""
        if attrs.get('flag') and not attrs.get('flag_reason'):
            raise serializers.ValidationError(
                "flag_reason is required when flagging a message"
            )
        if not attrs.get('flag') and attrs.get('is_helpful') is None:
            raise serializers.ValidationError(
                "Either provide helpfulness feedback or flag the message"
            )
        return attrs


class ConversationExportSerializer(serializers.Serializer):
    """Serializer for exporting conversations."""
    
    format = serializers.ChoiceField(choices=['json', 'csv', 'pdf'], default='json')
    include_metadata = serializers.BooleanField(default=False)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)