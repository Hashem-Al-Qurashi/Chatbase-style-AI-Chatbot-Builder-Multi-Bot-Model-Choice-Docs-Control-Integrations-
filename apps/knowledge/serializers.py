"""
Serializers for knowledge app.
Handles knowledge sources and chunks management.
"""

from rest_framework import serializers
from apps.knowledge.models import KnowledgeSource, KnowledgeChunk, CitationUsage


class KnowledgeSourceSerializer(serializers.ModelSerializer):
    """Knowledge source serializer."""
    
    chunk_count = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeSource
        fields = (
            'id', 'chatbot', 'name', 'description', 'source_type',
            'url', 'file_path', 'file_size', 'file_size_mb',
            'mime_type', 'is_active', 'is_citable',
            'processing_status', 'processed_at',
            'chunk_count', 'error_message',
            'created_at', 'updated_at', 'metadata'
        )
        read_only_fields = (
            'id', 'file_path', 'file_size', 'mime_type',
            'processing_status', 'processed_at',
            'chunk_count', 'error_message',
            'created_at', 'updated_at'
        )
    
    def get_chunk_count(self, obj):
        """Get number of chunks."""
        return obj.chunks.count()
    
    def get_file_size_mb(self, obj):
        """Get file size in MB."""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None


class KnowledgeChunkSerializer(serializers.ModelSerializer):
    """Knowledge chunk serializer."""
    
    source_name = serializers.CharField(source='source.name', read_only=True)
    source_type = serializers.CharField(source='source.source_type', read_only=True)
    
    class Meta:
        model = KnowledgeChunk
        fields = (
            'id', 'source', 'source_name', 'source_type',
            'content', 'chunk_index', 'chunk_hash',
            'embedding_model', 'is_citable',
            'created_at', 'metadata'
        )
        read_only_fields = fields


class CitationUsageSerializer(serializers.ModelSerializer):
    """Citation usage serializer."""
    
    source_name = serializers.CharField(source='source.name', read_only=True)
    chatbot_name = serializers.CharField(source='chatbot.name', read_only=True)
    
    class Meta:
        model = CitationUsage
        fields = (
            'id', 'chatbot', 'chatbot_name', 'source',
            'source_name', 'chunk', 'conversation_id',
            'message_id', 'query', 'relevance_score',
            'created_at'
        )
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload."""
    
    chatbot_id = serializers.UUIDField(required=True)
    file = serializers.FileField(required=True)
    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False)
    is_citable = serializers.BooleanField(default=True)
    
    def validate_file(self, value):
        """Validate uploaded file."""
        # Check file size (max 50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 50MB")
        
        # Check file type
        allowed_types = [
            'application/pdf',
            'text/plain',
            'text/csv',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'text/html',
            'text/markdown'
        ]
        
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(f"File type {value.content_type} not supported")
        
        return value


class URLProcessSerializer(serializers.Serializer):
    """Serializer for URL processing."""
    
    chatbot_id = serializers.UUIDField(required=True)
    url = serializers.URLField(required=True)
    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False)
    is_citable = serializers.BooleanField(default=True)
    crawl_depth = serializers.IntegerField(default=1, min_value=1, max_value=3)


class YoutubeProcessSerializer(serializers.Serializer):
    """Serializer for YouTube video processing."""
    
    chatbot_id = serializers.UUIDField(required=True)
    video_url = serializers.URLField(required=True)
    name = serializers.CharField(required=False, max_length=255)
    description = serializers.CharField(required=False)
    is_citable = serializers.BooleanField(default=True)
    include_transcript = serializers.BooleanField(default=True)
    include_comments = serializers.BooleanField(default=False)
    
    def validate_video_url(self, value):
        """Validate YouTube URL."""
        import re
        youtube_pattern = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        
        if not youtube_pattern.match(value):
            raise serializers.ValidationError("Invalid YouTube URL")
        
        return value


class KnowledgeSearchSerializer(serializers.Serializer):
    """Serializer for knowledge search."""
    
    query = serializers.CharField(required=True, max_length=1000)
    chatbot_id = serializers.UUIDField(required=False)
    source_types = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'document', 'url', 'youtube', 'api'
        ]),
        required=False
    )
    is_citable_only = serializers.BooleanField(default=False)
    limit = serializers.IntegerField(default=10, min_value=1, max_value=50)