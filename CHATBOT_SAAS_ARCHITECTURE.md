# Full Architecture for Simple Chatbot Builder SaaS

## System Overview
You're building a RAG-based chatbot SaaS where users upload knowledge sources, train a chatbot, and deploy it via shareable link or iframe embed. The CRM integration allows bidirectional data flow (fetch customer data, push leads).

---

## 1. **Frontend Architecture**

### Technology
- **React** (Vite for speed, or Next.js if you need SSR for marketing pages)
- **State Management**: React Context or Zustand (avoid Redux overkill)
- **UI Library**: Tailwind CSS + Shadcn/UI or Chakra UI
- **HTTP Client**: Axios or native fetch with proper error boundaries

### Key Pages/Components
1. **Auth Flow**
   - Login/Register (email/password)
   - Google OAuth redirect handler
   - Password reset flow

2. **Dashboard**
   - List user's chatbots (card grid)
   - Create new chatbot button
   - Usage stats (messages remaining, plan tier)

3. **Chatbot Builder Wizard**
   - Step 1: Name & description
   - Step 2: Add knowledge sources (file upload, URL input, optional video URL)
   - Step 3: Privacy controls (toggle each source: "Citable" vs "Learn Only")
   - Step 4: Review & train (show progress bar)

4. **Chatbot Settings Page**
   - Shareable link (copy button)
   - Iframe embed code (copy snippet)
   - CRM webhook configuration (input webhook URL, test button)
   - Delete chatbot

5. **Chat Interface** (embedded & standalone)
   - Floating bubble widget (iframe-able)
   - Message list with source citations (only for "Citable" content)
   - Input box with rate limiting based on plan

6. **Billing/Settings**
   - Stripe Customer Portal redirect
   - Plan upgrade UI

---

## 2. **Backend Architecture**

### Technology Stack
- **Framework**: Django + Django REST Framework (DRF)
  - Why Django: Built-in admin, ORM, mature ecosystem, easy to extend
  - Alternative: FastAPI (faster, but you lose Django admin and ORM maturity)
  
- **Task Queue**: Celery + Redis
  - For async jobs: file processing, URL crawling, embedding generation
  
- **Web Server**: Gunicorn + Nginx (production)

### API Design (RESTful)

```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/oauth/google
GET    /api/auth/me

GET    /api/chatbots/              # List user's chatbots
POST   /api/chatbots/              # Create chatbot
GET    /api/chatbots/{id}/         # Get chatbot details
PATCH  /api/chatbots/{id}/         # Update settings
DELETE /api/chatbots/{id}/         # Delete chatbot

POST   /api/chatbots/{id}/sources/ # Add knowledge source
DELETE /api/chatbots/{id}/sources/{source_id}/

POST   /api/chatbots/{id}/train/   # Trigger training job
GET    /api/chatbots/{id}/status/  # Check training status

POST   /api/chat/{chatbot_id}/     # Send message (public endpoint)
GET    /api/chat/{chatbot_id}/history/

POST   /api/webhooks/stripe/       # Stripe webhook handler
POST   /api/webhooks/crm/          # Generic CRM webhook receiver
```

---

## 3. **Database Schema** (PostgreSQL)

### Core Tables

```sql
-- Users
users
  id (PK)
  email (unique)
  password_hash
  google_id (nullable, unique)
  stripe_customer_id (nullable)
  plan_tier (enum: free, pro, enterprise)
  message_quota (int)
  messages_used (int)
  created_at, updated_at

-- Chatbots
chatbots
  id (PK)
  user_id (FK -> users)
  name
  description
  public_url_slug (unique)
  crm_webhook_url (nullable)
  created_at, updated_at

-- Knowledge Sources
knowledge_sources
  id (PK)
  chatbot_id (FK -> chatbots, cascade delete)
  source_type (enum: file, url, video)
  source_url (nullable)
  file_path (nullable, S3 key)
  is_citable (boolean, default true)  # Privacy flag
  status (enum: pending, processing, ready, failed)
  error_message (nullable)
  created_at, updated_at

-- Conversations
conversations
  id (PK)
  chatbot_id (FK -> chatbots)
  session_id (UUID)
  created_at

-- Messages
messages
  id (PK)
  conversation_id (FK -> conversations)
  role (enum: user, assistant)
  content (text)
  sources_used (JSONB, array of source IDs)  # Only citable sources
  created_at
```

### Vector Storage (pgvector)

```sql
-- Embeddings table (if using pgvector in Postgres)
embeddings
  id (PK)
  knowledge_source_id (FK -> knowledge_sources)
  chunk_text (text)
  embedding (vector(1536))  # OpenAI ada-002 dimension
  metadata (JSONB)  # {page_num, section, etc.}
  created_at

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

**Alternative**: Use **Pinecone** or **Weaviate** instead of pgvector (easier scaling, managed service).

---

## 4. **Core Backend Services/Modules**

### 4.1 Authentication Service
- Email/password with bcrypt hashing
- JWT token generation (access + refresh)
- Google OAuth2 flow (use `python-social-auth` or `django-allauth`)
- Token refresh endpoint

### 4.2 File Processing Service (Celery Task)
```python
@celery.task
def process_file(source_id):
    source = KnowledgeSource.objects.get(id=source_id)
    
    # Download from S3
    file_content = download_from_s3(source.file_path)
    
    # Extract text based on type
    if source.source_type == 'pdf':
        text = extract_pdf_text(file_content)  # PyPDF2 or pdfplumber
    elif source.source_type == 'docx':
        text = extract_docx_text(file_content)  # python-docx
    elif source.source_type == 'txt':
        text = file_content.decode('utf-8')
    
    # Chunk text (RecursiveCharacterTextSplitter from LangChain)
    chunks = chunk_text(text, chunk_size=1000, overlap=200)
    
    # Generate embeddings
    embeddings = openai.Embedding.create(
        input=chunks,
        model="text-embedding-ada-002"
    )
    
    # Store in pgvector or Pinecone
    store_embeddings(source_id, chunks, embeddings)
    
    # Update status
    source.status = 'ready'
    source.save()
```

### 4.3 URL Crawler Service (Celery Task)
```python
@celery.task
def crawl_url(source_id):
    source = KnowledgeSource.objects.get(id=source_id)
    
    # Fetch HTML (use requests + BeautifulSoup)
    response = requests.get(source.source_url, timeout=10)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract main content (heuristic: remove nav/footer/scripts)
    text = extract_main_content(soup)
    
    # Same chunking + embedding flow as files
    # ...
```

### 4.4 RAG Query Service
```python
def generate_response(chatbot_id, user_message):
    # 1. Generate query embedding
    query_embedding = openai.Embedding.create(
        input=user_message,
        model="text-embedding-ada-002"
    )
    
    # 2. Vector similarity search (pgvector or Pinecone)
    # CRITICAL: Only search embeddings where source.is_citable = True
    relevant_chunks = search_embeddings(
        chatbot_id=chatbot_id,
        query_embedding=query_embedding,
        top_k=5,
        filter_citable=True  # Enforce privacy
    )
    
    # 3. Build context (include ALL chunks, even "learn only" ones)
    # But mark which are citable
    context = build_context(relevant_chunks)
    
    # 4. Call LLM with system prompt enforcing citation rules
    system_prompt = f"""
    You are a helpful chatbot. Answer using the context below.
    CRITICAL RULES:
    - Only cite sources marked as [CITABLE]
    - Never mention or reference [PRIVATE] sources in your response
    - If you use private context for reasoning, do not reveal it
    
    Context:
    {context}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    
    # 5. Extract sources used (only citable ones)
    sources = extract_cited_sources(relevant_chunks)
    
    return {
        "message": response.choices[0].message.content,
        "sources": sources
    }
```

**Critical Privacy Implementation:**
- **Database query level**: Filter embeddings by `knowledge_sources.is_citable = TRUE` when fetching for citations
- **LLM prompt level**: Instruct the model to never mention private sources
- **Response parsing**: Strip any leaked source IDs from private content

---

## 5. **Third-Party Integrations**

### 5.1 Stripe (Payments)
- **Setup**: Install `stripe` Python library
- **Flow**:
  1. User clicks "Upgrade to Pro"
  2. Backend creates Stripe Checkout session
  3. Redirect user to Stripe hosted page
  4. On success, Stripe webhook hits `/api/webhooks/stripe/`
  5. Update `users.plan_tier` and `message_quota`

```python
@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    
    event = stripe.Webhook.construct_event(
        payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user = User.objects.get(stripe_customer_id=session['customer'])
        user.plan_tier = 'pro'
        user.message_quota = 1000
        user.save()
    
    return HttpResponse(status=200)
```

### 5.2 CRM Integration (Generic Webhook)
**Two directions:**

**A) Push leads to CRM** (when user submits email in chat)
```python
def push_lead_to_crm(chatbot, email, name, phone):
    if not chatbot.crm_webhook_url:
        return
    
    payload = {
        "email": email,
        "name": name,
        "phone": phone,
        "source": f"chatbot_{chatbot.id}"
    }
    
    requests.post(chatbot.crm_webhook_url, json=payload, timeout=5)
```

**B) Fetch customer data from CRM** (bidirectional)
- Expose a webhook endpoint that CRMs can call to push data
- Or implement OAuth for specific CRMs (HubSpot, Salesforce) - but this is scope creep
- For MVP: Just push-only webhook is sufficient

---

## 6. **Embed Widget Architecture**

### Frontend (Embedded Chat Bubble)
```html
<!-- User copies this snippet -->
<script>
  (function() {
    var chatbot = document.createElement('iframe');
    chatbot.src = 'https://yourdomain.com/embed/{chatbot_id}';
    chatbot.style.cssText = 'position:fixed;bottom:20px;right:20px;width:400px;height:600px;border:none;z-index:9999';
    document.body.appendChild(chatbot);
  })();
</script>
```

### Backend Embed Endpoint
- `/embed/{chatbot_id}/` serves a minimal HTML page with chat UI
- No auth required (public endpoint)
- Rate limited by IP + session cookie
- CORS headers allow iframe embedding

---

## 7. **Infrastructure & Deployment**

### Development
- **Local**: Docker Compose (Postgres, Redis, Celery worker)
- **Environment vars**: `.env` file for secrets

### Production
- **Hosting**: Heroku, Render, Fly.io, or AWS EC2 + RDS
- **Database**: AWS RDS (Postgres with pgvector extension)
- **File Storage**: AWS S3 (for uploaded docs)
- **Vector DB**: Pinecone (managed) or pgvector (self-hosted)
- **Task Queue**: Redis on Heroku/Render or AWS ElastiCache
- **CDN**: Cloudflare (for embed widget assets)

### Security
- **HTTPS only** (Let's Encrypt or Cloudflare)
- **CORS**: Restrictive for API, permissive for embed endpoint
- **Rate limiting**: Django Ratelimit or Nginx
- **Input sanitization**: Validate all file uploads (MIME type, size)

---

## 8. **Critical Implementation Notes**

### Privacy Enforcement (Learn-Only Sources)
**This is your biggest risk area.** Here's how to prevent leaks:

1. **Database query filter**:
   ```python
   citable_embeddings = Embedding.objects.filter(
       knowledge_source__chatbot_id=chatbot_id,
       knowledge_source__is_citable=True
   )
   ```

2. **LLM prompt engineering**:
   ```
   CRITICAL: You have access to two types of context:
   - [CITABLE]: You may reference these sources
   - [PRIVATE]: Use for reasoning ONLY, never mention them
   ```

3. **Post-processing**: Strip any `source_id` references from private sources in the response

4. **Testing**: Create test cases where private sources contain unique keywords, verify they never appear in responses

### CRM Integration Scope
For $1,200 MVP, **do NOT build native CRM integrations**. Instead:
- Provide a generic webhook URL input field
- User configures their CRM to call your webhook
- You POST lead data to their webhook URL
- This keeps you out of OAuth/API hell for 10 different CRMs

### Video Processing
If user pastes a YouTube URL:
- Use `youtube-transcript-api` library to fetch transcript
- Store transcript as text, process like any other document
- This is cheaper than transcribing with Whisper

---

## 9. **Recommended Tech Choices**

| Component | Choice | Why |
|-----------|--------|-----|
| Backend Framework | Django + DRF | Admin panel, ORM, ecosystem |
| Vector DB | Pinecone | Managed, easy scaling, $70/mo free tier |
| File Storage | AWS S3 | Industry standard, cheap |
| Task Queue | Celery + Redis | Battle-tested, works with Django |
| Embeddings | OpenAI ada-002 | Cheap ($0.0001/1K tokens), fast |
| LLM | GPT-3.5-turbo | Cheap, fast enough for chat |
| Auth | django-allauth | Handles OAuth + email out of box |

---

## 10. **What NOT to Build (Scope Creep Traps)**

❌ Multi-provider support (Anthropic, Gemini) - OpenAI only for MVP  
❌ Fine-tuning - RAG is sufficient  
❌ Analytics dashboard - Use Django admin  
❌ White-label/agency features - Single-tenant only  
❌ Auto-sync for Drive/Sheets - Manual refresh button only  
❌ Voice/audio - Text only  
❌ Custom branding - One default theme  

---

## 11. **Implementation Timeline - Phase-Based Approach**

**Phase 1**: Authentication & Security (COMPLETED ✅)
- JWT authentication system
- User registration and login APIs
- Google OAuth2 integration
- API security and middleware
- Password reset flow

**Phase 2**: Knowledge Processing Pipeline (4 weeks)
- Week 0: Security hardening (CRITICAL - BLOCKING)
- Week 1: Document processing and validation
- Week 2: Text chunking and embedding generation
- Week 3: Vector storage and background processing
- Week 4: Quality assurance and monitoring

**Phase 3**: RAG Query Engine (3 weeks)
- Vector search optimization
- Context retrieval and ranking
- Response generation with LLM
- Privacy filter implementation

**Phase 4**: Chat Interface & APIs (3 weeks)
- Chat API endpoints
- Real-time conversation handling
- Public chatbot APIs
- Rate limiting per plan

**Phase 5**: Background Task Processing (2 weeks)
- Celery optimization
- Progress tracking
- Error recovery
- Performance monitoring

**Phase 6**: Billing & Subscription (3 weeks)
- Stripe integration
- Plan management
- Usage tracking
- Webhook processing

**Phase 7**: Frontend & Widget (4 weeks)
- React dashboard
- Embeddable chat widget
- User interface
- Final testing and deployment

---

## 12. **Budget Reality Check**

At $1,200 for this scope, you're being massively undercharged. Realistic rates:
- **Offshore dev (India/Pakistan)**: $2,500-4,000
- **Eastern Europe**: $5,000-8,000
- **US/Western Europe**: $10,000-15,000

Your client is either:
- Testing you with a small project before bigger work
- Expecting bare-bones quality
- Unaware of market rates

**My advice**: Deliver a solid MVP, document everything well, and use this as leverage for the "$12k/month projects" they mentioned. This is your foot in the door.