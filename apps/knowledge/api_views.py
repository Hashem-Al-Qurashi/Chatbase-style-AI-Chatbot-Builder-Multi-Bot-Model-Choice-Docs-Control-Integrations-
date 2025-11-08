"""
API views for knowledge app.
Handles knowledge source management and processing.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
import structlog
import hashlib

from apps.knowledge.models import KnowledgeSource, KnowledgeChunk, CitationUsage
from apps.chatbots.models import Chatbot
from apps.knowledge.serializers import (
    KnowledgeSourceSerializer, KnowledgeChunkSerializer,
    CitationUsageSerializer, DocumentUploadSerializer,
    URLProcessSerializer, YoutubeProcessSerializer,
    KnowledgeSearchSerializer
)
# TODO: Import these when tasks are implemented
# from apps.core.tasks import (
#     process_document_task,
#     process_url_task,
#     process_youtube_task
# )

# TODO: Import when vector search is implemented
# from apps.core.vector_search import VectorSearchService

logger = structlog.get_logger()


class KnowledgeSourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for knowledge source management.
    """
    serializer_class = KnowledgeSourceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter knowledge sources by user's chatbots."""
        user = self.request.user
        queryset = KnowledgeSource.objects.filter(chatbot__user=user)
        
        # Filter by chatbot
        chatbot_id = self.request.query_params.get('chatbot')
        if chatbot_id:
            queryset = queryset.filter(chatbot_id=chatbot_id)
        
        # Filter by source type
        source_type = self.request.query_params.get('source_type')
        if source_type:
            queryset = queryset.filter(source_type=source_type)
        
        # Filter by status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        # Filter by citability
        is_citable = self.request.query_params.get('is_citable')
        if is_citable is not None:
            queryset = queryset.filter(is_citable=is_citable.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        queryset = queryset.order_by(ordering)
        
        return queryset.select_related('chatbot')
    
    def perform_destroy(self, instance):
        """Delete knowledge source and its chunks."""
        # TODO: Delete from vector store when implemented
        # vector_service = VectorSearchService()
        # vector_service.delete_source(str(instance.id))
        
        # Delete file if exists
        if instance.file_path:
            import os
            if os.path.exists(instance.file_path):
                os.remove(instance.file_path)
        
        super().perform_destroy(instance)
        
        logger.info(
            "Knowledge source deleted",
            source_id=str(instance.id),
            chatbot_id=str(instance.chatbot.id)
        )
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Reprocess a knowledge source."""
        source = self.get_object()
        
        if source.processing_status == 'processing':
            return Response(
                {'error': 'Source is already being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Trigger reprocessing when tasks are implemented
        # if source.source_type == 'document':
        #     process_document_task.delay(str(source.id))
        # elif source.source_type == 'url':
        #     process_url_task.delay(str(source.id))
        # elif source.source_type == 'youtube':
        #     process_youtube_task.delay(str(source.id))
        # else:
        #     return Response(
        #         {'error': f'Cannot reprocess source type: {source.source_type}'},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        
        source.processing_status = 'processing'
        source.error_message = None
        source.save()
        
        logger.info(
            "Knowledge source reprocessing initiated",
            source_id=str(source.id),
            source_type=source.source_type
        )
        
        return Response({
            'message': 'Reprocessing initiated',
            'status': 'processing'
        })
    
    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """Get chunks for a knowledge source."""
        source = self.get_object()
        chunks = source.chunks.all().order_by('chunk_index')
        
        # Pagination
        page = self.paginate_queryset(chunks)
        if page is not None:
            serializer = KnowledgeChunkSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = KnowledgeChunkSerializer(chunks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def citations(self, request, pk=None):
        """Get citation usage for a knowledge source."""
        source = self.get_object()
        citations = CitationUsage.objects.filter(source=source).order_by('-created_at')
        
        # Add date filtering
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        if date_from:
            citations = citations.filter(created_at__gte=date_from)
        if date_to:
            citations = citations.filter(created_at__lte=date_to)
        
        # Pagination
        page = self.paginate_queryset(citations)
        if page is not None:
            serializer = CitationUsageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CitationUsageSerializer(citations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search across knowledge sources."""
        serializer = KnowledgeSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        query = serializer.validated_data['query']
        chatbot_id = serializer.validated_data.get('chatbot_id')
        source_types = serializer.validated_data.get('source_types')
        is_citable_only = serializer.validated_data.get('is_citable_only', False)
        limit = serializer.validated_data.get('limit', 10)
        
        # Build filters
        filters = {}
        if chatbot_id:
            filters['chatbot_id'] = str(chatbot_id)
        if source_types:
            filters['source_types'] = source_types
        if is_citable_only:
            filters['is_citable'] = True
        
        # TODO: Search using vector service when implemented
        # vector_service = VectorSearchService()
        # results = vector_service.search(
        #     query=query,
        #     filters=filters,
        #     limit=limit
        # )
        results = []  # Placeholder
        
        # Format results
        formatted_results = []
        for result in results:
            chunk = KnowledgeChunk.objects.get(id=result['chunk_id'])
            formatted_results.append({
                'chunk': KnowledgeChunkSerializer(chunk).data,
                'relevance_score': result['score'],
                'highlights': result.get('highlights', [])
            })
        
        return Response({
            'query': query,
            'results': formatted_results,
            'count': len(formatted_results)
        })


class KnowledgeChunkViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for knowledge chunk viewing.
    Read-only as chunks are managed automatically.
    """
    serializer_class = KnowledgeChunkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter chunks by user's chatbots."""
        user = self.request.user
        queryset = KnowledgeChunk.objects.filter(source__chatbot__user=user)
        
        # Filter by source
        source_id = self.request.query_params.get('source')
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        
        # Filter by chatbot
        chatbot_id = self.request.query_params.get('chatbot')
        if chatbot_id:
            queryset = queryset.filter(source__chatbot_id=chatbot_id)
        
        # Filter by citability
        is_citable = self.request.query_params.get('is_citable')
        if is_citable is not None:
            queryset = queryset.filter(is_citable=is_citable.lower() == 'true')
        
        # Search content
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(content__icontains=search)
        
        # Ordering
        ordering = self.request.query_params.get('ordering', 'chunk_index')
        queryset = queryset.order_by(ordering)
        
        return queryset.select_related('source')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    """
    Upload and process a document.
    """
    serializer = DocumentUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Get chatbot
    chatbot = get_object_or_404(
        Chatbot,
        id=serializer.validated_data['chatbot_id'],
        user=request.user
    )
    
    # Get uploaded file
    uploaded_file = serializer.validated_data['file']
    
    # Import the document processing service
    from apps.core.document_processing_service import DocumentProcessingService
    
    # Create file path
    import os
    from django.conf import settings
    from django.utils.text import slugify
    import uuid
    
    file_name = f"{uuid.uuid4()}_{slugify(uploaded_file.name)}"
    file_path = os.path.join(settings.MEDIA_ROOT, 'knowledge', str(chatbot.id), file_name)
    
    # Create directory if not exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Read file content BEFORE saving to avoid buffer consumption
    file_content = uploaded_file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Reset file pointer for saving
    uploaded_file.seek(0)
    
    # Save file
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    
    # STEP 1 FIX: Map file extension to correct content_type and MIME type
    # This fixes the critical mismatch between frontend types and backend processing
    file_extension = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
    
    # Map file extensions to both content_type (for model) and mime_type (for processor)
    file_type_mapping = {
        'pdf': {
            'content_type': 'pdf',
            'mime_type': 'application/pdf'
        },
        'docx': {
            'content_type': 'docx', 
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        'doc': {  # Treat .doc as .docx for processing
            'content_type': 'docx',
            'mime_type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        },
        'txt': {
            'content_type': 'txt',
            'mime_type': 'text/plain'
        }
    }
    
    # Get mapped types or defaults for unsupported files
    mapping = file_type_mapping.get(file_extension, {
        'content_type': 'document',
        'mime_type': uploaded_file.content_type or 'application/octet-stream'
    })
    
    mapped_content_type = mapping['content_type']
    reliable_mime_type = mapping['mime_type']
    
    # Create knowledge source
    source = KnowledgeSource.objects.create(
        chatbot=chatbot,
        name=serializer.validated_data.get('name', uploaded_file.name),
        description=serializer.validated_data.get('description', ''),
        content_type=mapped_content_type,  # FIXED: Use mapped type instead of hardcoded 'document'
        file_path=file_path,
        file_size=uploaded_file.size,
        file_hash=file_hash,
        mime_type=reliable_mime_type,  # FIXED: Use reliable MIME type based on extension
        is_citable=serializer.validated_data.get('is_citable', True),
        status='pending',
        metadata={
            'original_filename': uploaded_file.name,
            'upload_timestamp': timezone.now().isoformat(),
            'file_extension': file_extension,
            'mapped_content_type': mapped_content_type,
            'original_mime_type': uploaded_file.content_type,
            'reliable_mime_type': reliable_mime_type
        }
    )
    
    # Process document immediately using the document processing service
    try:
        doc_service = DocumentProcessingService()
        result = doc_service.process_uploaded_file(
            knowledge_source=source,
            file_content=file_content,
            filename=uploaded_file.name,
            mime_type=reliable_mime_type  # FIXED: Use reliable MIME type for processing
        )
        
        if result.success:
            logger.info(
                "Document processed successfully",
                source_id=str(source.id),
                chatbot_id=str(chatbot.id),
                chunks_created=len(result.chunks),
                total_tokens=result.total_tokens,
                processing_time_ms=result.processing_time_ms
            )
        else:
            logger.error(
                "Document processing failed",
                source_id=str(source.id),
                error=result.error_message
            )
            
    except Exception as e:
        logger.error(
            "Document processing service error",
            source_id=str(source.id),
            error=str(e)
        )
        # Update source status to failed
        source.update_processing_status('failed', error_message=str(e))
    
    # Refresh source to get updated status
    source.refresh_from_db()
    
    logger.info(
        "Document uploaded and processed",
        source_id=str(source.id),
        chatbot_id=str(chatbot.id),
        file_name=uploaded_file.name,
        file_size=uploaded_file.size,
        final_status=source.status
    )
    
    return Response(
        KnowledgeSourceSerializer(source).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_url(request):
    """
    Process a URL as knowledge source.
    """
    serializer = URLProcessSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Get chatbot
    chatbot = get_object_or_404(
        Chatbot,
        id=serializer.validated_data['chatbot_id'],
        user=request.user
    )
    
    url = serializer.validated_data['url']
    
    # Import the document processing service
    from apps.core.document_processing_service import DocumentProcessingService
    
    # Calculate URL hash for deduplication
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    
    # Create knowledge source
    source = KnowledgeSource.objects.create(
        chatbot=chatbot,
        name=serializer.validated_data.get('name', url),
        description=serializer.validated_data.get('description', ''),
        content_type='url',
        source_url=url,
        file_hash=url_hash,
        is_citable=serializer.validated_data.get('is_citable', True),
        status='pending',
        metadata={
            'crawl_depth': serializer.validated_data.get('crawl_depth', 1),
            'original_url': url,
            'submission_timestamp': timezone.now().isoformat()
        }
    )
    
    # Process URL immediately using the document processing service
    try:
        doc_service = DocumentProcessingService()
        result = doc_service.process_url_content(
            knowledge_source=source,
            url=url
        )
        
        if result.success:
            logger.info(
                "URL processed successfully",
                source_id=str(source.id),
                chatbot_id=str(chatbot.id),
                chunks_created=len(result.chunks),
                total_tokens=result.total_tokens,
                processing_time_ms=result.processing_time_ms
            )
        else:
            logger.error(
                "URL processing failed",
                source_id=str(source.id),
                error=result.error_message
            )
            
    except Exception as e:
        logger.error(
            "URL processing service error",
            source_id=str(source.id),
            error=str(e)
        )
        # Update source status to failed
        source.update_processing_status('failed', error_message=str(e))
    
    # Refresh source to get updated status
    source.refresh_from_db()
    
    logger.info(
        "URL submitted and processed",
        source_id=str(source.id),
        chatbot_id=str(chatbot.id),
        url=url,
        final_status=source.status
    )
    
    return Response(
        KnowledgeSourceSerializer(source).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_youtube(request):
    """
    Process a YouTube video as knowledge source.
    """
    serializer = YoutubeProcessSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Get chatbot
    chatbot = get_object_or_404(
        Chatbot,
        id=serializer.validated_data['chatbot_id'],
        user=request.user
    )
    
    video_url = serializer.validated_data['video_url']
    
    # Extract video ID
    import re
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', video_url)
    video_id = video_id_match.group(1) if video_id_match else None
    
    if not video_id:
        raise ValidationError({'video_url': 'Could not extract video ID'})
    
    # Create knowledge source
    source = KnowledgeSource.objects.create(
        chatbot=chatbot,
        name=serializer.validated_data.get('name', f'YouTube: {video_id}'),
        description=serializer.validated_data.get('description', ''),
        content_type='youtube',
        source_url=video_url,
        is_citable=serializer.validated_data.get('is_citable', True),
        status='pending',
        metadata={
            'video_id': video_id,
            'include_transcript': serializer.validated_data.get('include_transcript', True),
            'include_comments': serializer.validated_data.get('include_comments', False)
        }
    )
    
    # TODO: Trigger processing task when implemented
    # process_youtube_task.delay(str(source.id))
    
    # For now, mark as ready for testing
    source.processing_status = 'ready'
    source.save()
    
    logger.info(
        "YouTube video submitted for processing",
        source_id=str(source.id),
        chatbot_id=str(chatbot.id),
        video_id=video_id
    )
    
    return Response(
        KnowledgeSourceSerializer(source).data,
        status=status.HTTP_201_CREATED
    )