# Phase 3 Implementation Plan - RAG Query Engine

## Document Purpose
This document outlines the comprehensive implementation strategy for Phase 3 (RAG Query Engine), following the architectural requirements and critical privacy enforcement specifications.

**Phase**: 3 of 7  
**Focus**: RAG Query Engine with Privacy Enforcement  
**Timeline**: 3 weeks  
**Prerequisites**: Phase 2 Complete ✅ (Knowledge Processing Pipeline)

---

## Executive Summary

### **Critical Requirements**
Phase 3 implements the core RAG (Retrieval-Augmented Generation) query engine that powers the chatbot's intelligence. The most critical aspect is the **privacy enforcement system** that ensures "learn-only" sources are NEVER exposed to end users.

### **Key Components**
1. **Vector Search Optimization**: Fast, accurate similarity search
2. **Context Retrieval & Ranking**: Smart context selection and prioritization
3. **Response Generation**: LLM integration with GPT-3.5-turbo
4. **Privacy Filter**: Multi-layer protection for non-citable sources

---

## Privacy Enforcement Architecture 🔒

### **Three-Layer Privacy Protection**

#### **Layer 1: Database Query Filter**
```python
# Only search citable embeddings for retrieval
citable_embeddings = Embedding.objects.filter(
    knowledge_source__chatbot_id=chatbot_id,
    knowledge_source__is_citable=True  # CRITICAL FILTER
)
```

#### **Layer 2: LLM Prompt Engineering**
```python
system_prompt = """
You are a helpful chatbot. Answer using the context below.
CRITICAL RULES:
- Only cite sources marked as [CITABLE]
- Never mention or reference [PRIVATE] sources in your response
- If you use private context for reasoning, do not reveal it
"""
```

#### **Layer 3: Response Post-Processing**
- Strip any leaked source IDs from private sources
- Validate no private content appears in response
- Audit logging for privacy violations

### **Testing Requirements**
- Create test cases with unique keywords in private sources
- Verify those keywords NEVER appear in responses
- Automated privacy leak detection

---

## Technical Architecture

### **Component Overview**
```
┌─────────────────┐
│  User Query     │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Embedder │ (OpenAI ada-002)
    └────┬────┘
         │
    ┌────▼────────────┐
    │ Vector Search   │ (Pinecone/pgvector)
    │ + Privacy Filter│
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │ Context Builder │
    │ + Ranker       │
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │ LLM Generator   │ (GPT-3.5-turbo)
    │ + Safety Layer  │
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │ Post-Processor  │
    │ + Privacy Audit │
    └────┬────────────┘
         │
    ┌────▼────────┐
    │  Response   │
    └─────────────┘
```

---

## Implementation Tasks

### **Task 1: Vector Search Service** (Week 1)
**Priority**: Critical  
**Estimated Time**: 5 days  

#### **Subtasks**:

1. **Create VectorSearchService class** (2 days)
```python
# apps/core/rag/vector_search.py
class VectorSearchService:
    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.vector_storage = self._get_vector_storage()
        
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_citable: bool = True,  # CRITICAL
        score_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search for similar vectors with privacy filtering"""
        
    def _apply_privacy_filter(self, results: List) -> List:
        """Ensure only citable sources are returned"""
        
    def _rerank_results(self, results: List, query: str) -> List:
        """Rerank results using cross-encoder for better relevance"""
```

2. **Implement multi-backend support** (1 day)
```python
class VectorBackendFactory:
    @staticmethod
    def create_backend(backend_type: str) -> VectorBackend:
        if backend_type == "pinecone":
            return PineconeBackend()
        elif backend_type == "pgvector":
            return PgVectorBackend()
        else:
            return SQLiteBackend()
```

3. **Add caching layer** (1 day)
```python
class VectorSearchCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
        
    def get_cached_results(self, query_hash: str) -> Optional[List]:
        """Return cached results if available and not expired"""
        
    def cache_results(self, query_hash: str, results: List):
        """Cache search results with TTL"""
```

4. **Performance optimization** (1 day)
- Implement batch search for multiple queries
- Add connection pooling for vector DB
- Optimize embedding dimension handling
- Add metrics collection for search latency

#### **Acceptance Criteria**:
- [ ] Vector search returns relevant results < 200ms
- [ ] Privacy filter ALWAYS excludes non-citable sources
- [ ] Caching reduces repeated search latency by 90%
- [ ] Multi-backend support working (Pinecone, pgvector, SQLite)
- [ ] Comprehensive test coverage for privacy scenarios

---

### **Task 2: Context Retrieval & Ranking** (Week 1-2)
**Priority**: Critical  
**Estimated Time**: 4 days  

#### **Subtasks**:

1. **Create ContextBuilder class** (2 days)
```python
# apps/core/rag/context_builder.py
class ContextBuilder:
    def __init__(self, max_context_tokens: int = 3000):
        self.max_tokens = max_context_tokens
        self.token_counter = TokenCounter()
        
    def build_context(
        self,
        search_results: List[SearchResult],
        include_private: bool = True  # For reasoning, not citation
    ) -> ContextData:
        """Build context with clear separation of citable/private"""
        
        context_parts = []
        for result in search_results:
            if result.is_citable:
                context_parts.append(f"[CITABLE-{result.id}] {result.content}")
            elif include_private:
                context_parts.append(f"[PRIVATE] {result.content}")
                
        return ContextData(
            full_context="\n\n".join(context_parts),
            citable_sources=self._extract_citable_sources(search_results),
            token_count=self.token_counter.count(context_parts)
        )
```

2. **Implement ranking strategies** (1 day)
```python
class RelevanceRanker:
    def rank_by_similarity(self, results: List) -> List:
        """Rank by vector similarity score"""
        
    def rank_by_recency(self, results: List) -> List:
        """Boost recent documents"""
        
    def rank_by_keyword_match(self, results: List, query: str) -> List:
        """Boost exact keyword matches"""
        
    def hybrid_rank(self, results: List, query: str) -> List:
        """Combine multiple ranking strategies"""
```

3. **Add diversity mechanisms** (1 day)
```python
class DiversityOptimizer:
    def maximize_coverage(self, results: List) -> List:
        """Ensure diverse sources in context"""
        
    def remove_redundancy(self, results: List) -> List:
        """Remove highly similar chunks"""
```

#### **Acceptance Criteria**:
- [ ] Context respects token limits
- [ ] Citable and private sources clearly separated
- [ ] Ranking improves response relevance
- [ ] Diversity prevents repetitive context
- [ ] Performance < 100ms for context building

---

### **Task 3: Response Generation with LLM** (Week 2)
**Priority**: Critical  
**Estimated Time**: 5 days  

#### **Subtasks**:

1. **Create LLMService class** (2 days)
```python
# apps/core/rag/llm_service.py
class LLMService:
    def __init__(self):
        self.openai_client = OpenAIClient()
        self.circuit_breaker = CircuitBreaker()
        self.cost_tracker = CostTracker()
        
    async def generate_response(
        self,
        context: ContextData,
        user_query: str,
        chatbot_config: ChatbotConfig
    ) -> GenerationResult:
        """Generate response with privacy enforcement"""
        
        system_prompt = self._build_system_prompt(
            chatbot_config,
            enforce_privacy=True
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self._format_query_with_context(
                user_query, context
            )}
        ]
        
        try:
            response = await self.circuit_breaker.call(
                self.openai_client.chat_completion,
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=chatbot_config.temperature,
                max_tokens=chatbot_config.max_response_tokens
            )
            
            # Track costs
            self.cost_tracker.track_generation(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens
            )
            
            return GenerationResult(
                content=response.choices[0].message.content,
                usage=response.usage,
                citations=self._extract_citations(response.content, context)
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
```

2. **Implement prompt templates** (1 day)
```python
class PromptTemplates:
    @staticmethod
    def get_system_prompt(chatbot_type: str, privacy_mode: str) -> str:
        """Get appropriate system prompt based on configuration"""
        
        base_prompt = """
        You are a helpful AI assistant for {company_name}.
        Answer questions based on the provided context.
        """
        
        privacy_rules = """
        CRITICAL PRIVACY RULES:
        1. Only cite sources explicitly marked as [CITABLE-X]
        2. NEVER mention or reference [PRIVATE] sources
        3. Use [PRIVATE] content for reasoning but don't reveal it
        4. If asked about private sources, say "I cannot provide that information"
        """
        
        return base_prompt + privacy_rules
```

3. **Add streaming support** (1 day)
```python
class StreamingLLMService(LLMService):
    async def generate_streaming_response(
        self,
        context: ContextData,
        user_query: str,
        chatbot_config: ChatbotConfig
    ) -> AsyncIterator[str]:
        """Stream response tokens as they're generated"""
        
        async for chunk in self.openai_client.stream_completion(...):
            # Privacy check on partial content
            if not self._contains_private_leak(chunk):
                yield chunk
```

4. **Implement fallback strategies** (1 day)
```python
class LLMFallbackStrategy:
    def handle_rate_limit(self) -> str:
        """Return graceful message when rate limited"""
        
    def handle_context_too_long(self, context: str) -> str:
        """Truncate context intelligently"""
        
    def handle_timeout(self) -> str:
        """Return partial response or cached response"""
```

#### **Acceptance Criteria**:
- [ ] LLM responses generated < 2 seconds
- [ ] Privacy rules NEVER violated
- [ ] Streaming reduces perceived latency
- [ ] Costs tracked accurately
- [ ] Fallbacks handle all error scenarios

---

### **Task 4: Privacy Filter Implementation** (Week 2-3)
**Priority**: CRITICAL 🚨  
**Estimated Time**: 5 days  

#### **Subtasks**:

1. **Create PrivacyFilter class** (2 days)
```python
# apps/core/rag/privacy_filter.py
class PrivacyFilter:
    def __init__(self):
        self.violation_logger = ViolationLogger()
        self.private_content_detector = PrivateContentDetector()
        
    def validate_response(
        self,
        response: str,
        context: ContextData
    ) -> FilterResult:
        """Validate response doesn't leak private content"""
        
        violations = []
        
        # Check for private source IDs
        if self._contains_private_ids(response, context):
            violations.append("Private source IDs detected")
            
        # Check for unique private keywords
        if self._contains_private_keywords(response, context):
            violations.append("Private keywords detected")
            
        # ML-based leak detection
        if self.private_content_detector.detect_leak(response, context):
            violations.append("Potential private content leak detected")
            
        if violations:
            self.violation_logger.log_violations(violations, response)
            return FilterResult(
                passed=False,
                violations=violations,
                sanitized_response=self._sanitize_response(response, context)
            )
            
        return FilterResult(passed=True)
```

2. **Implement content sanitization** (1 day)
```python
class ResponseSanitizer:
    def sanitize_response(
        self,
        response: str,
        private_patterns: List[str]
    ) -> str:
        """Remove any private content from response"""
        
        sanitized = response
        for pattern in private_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)
            
        return sanitized
```

3. **Add privacy testing framework** (1 day)
```python
class PrivacyTestSuite:
    def test_keyword_leakage(self):
        """Test with unique keywords in private sources"""
        
        # Add unique keyword to private source
        private_source = "UNIQUE_TEST_KEYWORD_XYZ123"
        
        # Generate response
        response = self.generate_test_response(private_source)
        
        # Assert keyword not in response
        assert "UNIQUE_TEST_KEYWORD_XYZ123" not in response
        
    def test_citation_filtering(self):
        """Ensure only citable sources appear in citations"""
        
    def test_adversarial_prompts(self):
        """Test against prompts trying to extract private data"""
```

4. **Create audit logging** (1 day)
```python
class PrivacyAuditLogger:
    def log_query(self, query: str, context: ContextData):
        """Log query and context for audit"""
        
    def log_response(self, response: str, citations: List):
        """Log response for audit"""
        
    def log_violation(self, violation_type: str, details: Dict):
        """Log privacy violations for investigation"""
        
    def generate_audit_report(self, time_range: tuple) -> Report:
        """Generate privacy audit report"""
```

#### **Acceptance Criteria**:
- [ ] Zero privacy leaks in test suite
- [ ] All responses pass privacy validation
- [ ] Audit logs capture all queries/responses
- [ ] Sanitization removes private content
- [ ] Performance impact < 50ms

---

### **Task 5: RAG Pipeline Integration** (Week 3)
**Priority**: High  
**Estimated Time**: 4 days  

#### **Subtasks**:

1. **Create RAGPipeline orchestrator** (2 days)
```python
# apps/core/rag/pipeline.py
class RAGPipeline:
    def __init__(self, chatbot_id: str):
        self.chatbot_id = chatbot_id
        self.vector_search = VectorSearchService(chatbot_id)
        self.context_builder = ContextBuilder()
        self.llm_service = LLMService()
        self.privacy_filter = PrivacyFilter()
        
    async def process_query(
        self,
        user_query: str,
        conversation_id: str
    ) -> RAGResponse:
        """Complete RAG pipeline execution"""
        
        try:
            # 1. Generate query embedding
            query_embedding = await self._generate_embedding(user_query)
            
            # 2. Search for relevant chunks (WITH PRIVACY FILTER)
            search_results = await self.vector_search.search(
                query_embedding,
                filter_citable=True  # CRITICAL
            )
            
            # 3. Build context
            context = self.context_builder.build_context(search_results)
            
            # 4. Generate response
            generation_result = await self.llm_service.generate_response(
                context, user_query, self._get_chatbot_config()
            )
            
            # 5. Apply privacy filter
            filter_result = self.privacy_filter.validate_response(
                generation_result.content, context
            )
            
            if not filter_result.passed:
                logger.warning(f"Privacy violation detected: {filter_result.violations}")
                response_content = filter_result.sanitized_response
            else:
                response_content = generation_result.content
                
            # 6. Save to conversation history
            await self._save_message(
                conversation_id,
                user_query,
                response_content,
                context.citable_sources
            )
            
            return RAGResponse(
                content=response_content,
                citations=context.citable_sources,
                usage=generation_result.usage
            )
            
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            return self._generate_fallback_response(e)
```

2. **Add monitoring and metrics** (1 day)
```python
class RAGMetrics:
    def track_query_latency(self, stage: str, duration_ms: float):
        """Track latency for each pipeline stage"""
        
    def track_relevance_score(self, query: str, response: str):
        """Track response relevance metrics"""
        
    def track_privacy_violations(self, violation_count: int):
        """Track privacy filter violations"""
        
    def get_pipeline_analytics(self) -> Dict:
        """Get comprehensive pipeline analytics"""
```

3. **Implement conversation management** (1 day)
```python
class ConversationManager:
    def create_conversation(self, chatbot_id: str, session_id: str):
        """Create new conversation"""
        
    def add_message(self, conversation_id: str, message: Message):
        """Add message to conversation history"""
        
    def get_conversation_context(self, conversation_id: str, limit: int = 5):
        """Get recent conversation context"""
        
    def cleanup_old_conversations(self, days_old: int = 30):
        """Clean up old conversations"""
```

#### **Acceptance Criteria**:
- [ ] End-to-end pipeline working
- [ ] Response time < 3 seconds
- [ ] Metrics tracked for all stages
- [ ] Conversation history persisted
- [ ] Error handling comprehensive

---

### **Task 6: API Endpoints & Integration** (Week 3)
**Priority**: High  
**Estimated Time**: 3 days  

#### **Subtasks**:

1. **Create Chat API endpoints** (1.5 days)
```python
# apps/api/v1/chat.py
class ChatViewSet(viewsets.ViewSet):
    @action(methods=['post'], detail=False, url_path='(?P<chatbot_id>[^/.]+)')
    def send_message(self, request, chatbot_id=None):
        """
        POST /api/v1/chat/{chatbot_id}/
        {
            "message": "User question",
            "session_id": "optional-session-id"
        }
        """
        
    @action(methods=['get'], detail=False)
    def get_history(self, request, chatbot_id=None):
        """
        GET /api/v1/chat/{chatbot_id}/history/
        """
        
    @action(methods=['post'], detail=False)
    def rate_response(self, request, chatbot_id=None):
        """
        POST /api/v1/chat/{chatbot_id}/rate/
        {
            "message_id": "123",
            "rating": 5,
            "feedback": "Optional feedback"
        }
        """
```

2. **Add public embed endpoints** (1 day)
```python
class PublicChatView(APIView):
    permission_classes = []  # Public endpoint
    throttle_classes = [AnonRateThrottle]
    
    def post(self, request, chatbot_slug):
        """Public endpoint for embedded chatbots"""
        
        # Validate chatbot exists and is public
        # Apply stricter rate limiting
        # Process query through RAG pipeline
```

3. **WebSocket support for streaming** (0.5 days)
```python
class ChatConsumer(AsyncWebsocketConsumer):
    async def receive(self, text_data):
        """Handle WebSocket messages for real-time chat"""
        
        # Stream responses token by token
        async for token in self.rag_pipeline.stream_response(...):
            await self.send(text_data=json.dumps({
                'type': 'token',
                'content': token
            }))
```

#### **Acceptance Criteria**:
- [ ] Chat API endpoints functional
- [ ] Public endpoints properly rate limited
- [ ] WebSocket streaming working
- [ ] API documentation complete
- [ ] Error responses consistent

---

## Testing Strategy

### **Unit Tests**
```python
tests/rag/
├── test_vector_search.py       # Vector search with privacy
├── test_context_builder.py     # Context building logic
├── test_llm_service.py         # LLM integration
├── test_privacy_filter.py      # CRITICAL: Privacy enforcement
├── test_rag_pipeline.py        # End-to-end pipeline
└── test_chat_api.py           # API endpoints
```

### **Integration Tests**
```python
tests/integration/
├── test_rag_flow.py            # Complete RAG flow
├── test_privacy_scenarios.py   # Privacy leak prevention
├── test_performance.py         # Latency and throughput
└── test_error_recovery.py      # Error handling
```

### **Privacy Test Suite** 🔒
```python
tests/privacy/
├── test_keyword_leakage.py     # Unique keyword tests
├── test_citation_filtering.py  # Citation accuracy
├── test_adversarial_prompts.py # Attack scenarios
├── test_audit_logging.py       # Audit trail verification
└── test_sanitization.py        # Response sanitization
```

---

## Performance Requirements

### **Latency Targets**
- Query embedding: < 100ms
- Vector search: < 200ms
- Context building: < 100ms
- LLM generation: < 2000ms
- Privacy filtering: < 50ms
- **Total end-to-end: < 2.5 seconds**

### **Throughput Targets**
- 100 concurrent queries
- 1000 queries/minute sustained
- 10,000 queries/hour peak

### **Resource Limits**
- Memory usage < 1GB per worker
- CPU usage < 80% sustained
- Database connections < 50

---

## Risk Mitigation

### **High Risk: Privacy Leaks** 🚨
**Mitigation**:
- Three-layer privacy protection
- Comprehensive test suite
- Audit logging
- Regular security reviews
- Automated leak detection

### **Medium Risk: LLM Costs**
**Mitigation**:
- Caching frequent queries
- Token limit enforcement
- Cost tracking and alerts
- Rate limiting per user

### **Medium Risk: Performance**
**Mitigation**:
- Caching at multiple layers
- Async processing
- Database query optimization
- Load testing

---

## Success Metrics

### **Functional Metrics**
- [ ] 100% of queries return responses
- [ ] 0% privacy leak rate
- [ ] 95% responses < 3 seconds
- [ ] 90% user satisfaction rating

### **Technical Metrics**
- [ ] >90% test coverage
- [ ] Zero critical security issues
- [ ] <1% error rate
- [ ] 99.9% uptime

### **Business Metrics**
- [ ] Cost per query < $0.01
- [ ] Support tickets < 5% of queries
- [ ] User retention > 80%

---

## Definition of Done

### **Phase 3 Complete When:**
- [ ] All RAG components implemented
- [ ] Privacy enforcement verified with 0 leaks
- [ ] API endpoints fully functional
- [ ] Performance targets met
- [ ] Test coverage > 90%
- [ ] Documentation complete
- [ ] Security review passed
- [ ] Production deployment ready

### **Ready for Phase 4 When:**
- [ ] RAG pipeline stable and reliable
- [ ] Privacy protection proven
- [ ] Chat APIs ready for frontend
- [ ] Performance optimized

---

## Implementation Schedule

### **Week 1** (Days 1-5)
- Day 1-2: Vector Search Service core implementation
- Day 3: Multi-backend support
- Day 4: Caching layer
- Day 5: Performance optimization & testing

### **Week 2** (Days 6-10)
- Day 6-7: Context Builder implementation
- Day 8: Ranking strategies
- Day 9-10: LLM Service with privacy prompt

### **Week 3** (Days 11-15)
- Day 11-12: Privacy Filter implementation (CRITICAL)
- Day 13: RAG Pipeline integration
- Day 14: API endpoints
- Day 15: Final testing and documentation

---

## Notes

**Critical Success Factor**: The privacy filter is the most important component. Without proper privacy enforcement, the entire system fails compliance requirements.

**Testing Priority**: Privacy leak prevention tests must pass 100% before any deployment.

**Next Phase**: Phase 4 will build the Chat Interface & APIs, leveraging the RAG engine built in Phase 3.