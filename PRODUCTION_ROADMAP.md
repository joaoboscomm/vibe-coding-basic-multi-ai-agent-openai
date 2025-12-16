# 🚀 Production Readiness Roadmap

> **Project:** Multi-Agent Customer Support System  
> **Assessment Date:** December 2024  
> **Target:** Production Deployment

---

## 📊 Executive Summary

This document outlines all identified gaps and required implementations to make this multi-agent AI system production-ready. Items are prioritized by criticality and organized into implementation phases.

---

## 🔴 Phase 1: Critical (Before Production)

### 1.1 Authentication & Authorization

**Files to modify:** `config/settings.py`, `apps/support/views.py`

```python
# config/settings.py - Add these settings

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '100/minute',
        'chat': '30/minute',
    },
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
}
```

**Dependencies to add:**
```
djangorestframework-simplejwt==5.3.1
```

---

### 1.2 Rate Limiting

**File:** `apps/support/views.py`

```python
from rest_framework.throttling import ScopedRateThrottle

class ChatView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'chat'
```

---

### 1.3 LLM Timeout & Retry Logic

**File:** `apps/agents/base.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_openai import ChatOpenAI

class BaseAgent(ABC):
    def __init__(self, ...):
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            request_timeout=30,  # ADD THIS
            max_retries=3,       # ADD THIS
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def invoke_llm(self, messages: list) -> str:
        """Invoke the LLM with retry logic."""
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            raise
```

**Dependencies to add:**
```
tenacity==8.2.3
```

---

### 1.4 Database Indexes

**File:** `apps/core/models.py`

```python
class Message(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['role', 'created_at']),
        ]
        ordering = ['created_at']


class Conversation(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer_id', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['updated_at']),
        ]


class KnowledgeDocument(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_active', 'created_at']),
        ]
```

**File:** `apps/support/models.py`

```python
class Customer(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active', 'created_at']),
        ]


class Subscription(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'end_date']),
        ]


class Invoice(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['invoice_number']),
        ]


class SupportTicket(BaseModel):
    # ... existing fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
```

**File:** `scripts/init_pgvector.sql` - Add HNSW index

```sql
-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create HNSW index for fast similarity search (add after table creation)
-- Run this after migrations:
CREATE INDEX IF NOT EXISTS knowledge_documents_embedding_idx 
ON knowledge_documents 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

### 1.5 Production Security Settings

**File:** `config/settings_production.py` (NEW FILE)

```python
"""
Production-specific Django settings.
"""
from .settings import *

# Security
DEBUG = False
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# HTTPS Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True

# CORS - Explicit origins only
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')

# Logging - JSON format for production
LOGGING['handlers']['console']['formatter'] = 'json'

# Cache
CACHES['default']['OPTIONS'] = {
    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
    'CONNECTION_POOL_KWARGS': {'max_connections': 50},
}

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = 60
DATABASES['default']['CONN_HEALTH_CHECKS'] = True
```

---

## 🟡 Phase 2: High Priority (First Week)

### 2.1 Unit & Integration Tests

**File structure to create:**

```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_agents/
│   │   ├── __init__.py
│   │   ├── test_base_agent.py
│   │   ├── test_router_agent.py
│   │   ├── test_faq_agent.py
│   │   ├── test_order_agent.py
│   │   └── test_orchestrator.py
│   ├── test_tools/
│   │   ├── __init__.py
│   │   ├── test_vector_search.py
│   │   ├── test_db_lookup.py
│   │   └── test_ticket.py
│   ├── test_memory.py
│   ├── test_serializers.py
│   └── test_views.py
├── integration/
│   ├── __init__.py
│   ├── test_chat_flow.py
│   ├── test_rag_pipeline.py
│   └── test_celery_tasks.py
└── e2e/
    ├── __init__.py
    └── test_frontend.py
```

**File:** `tests/conftest.py`

```python
import pytest
from django.test import Client
from rest_framework.test import APIClient
from unittest.mock import Mock, patch

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def mock_openai():
    with patch('langchain_openai.ChatOpenAI') as mock:
        mock_instance = Mock()
        mock_instance.invoke.return_value = Mock(content="Test response")
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def sample_customer(db):
    from apps.support.models import Customer
    return Customer.objects.create(
        email="test@example.com",
        first_name="Test",
        last_name="User",
        company_name="Test Co"
    )

@pytest.fixture
def sample_conversation(db):
    from apps.core.models import Conversation
    return Conversation.objects.create(
        title="Test Conversation",
        status="active"
    )
```

**File:** `tests/unit/test_agents/test_router_agent.py`

```python
import pytest
from unittest.mock import Mock, patch
from apps.agents.router import RouterAgent

class TestRouterAgent:
    
    @pytest.fixture
    def router(self, sample_conversation, mock_openai):
        return RouterAgent(
            conversation_id=sample_conversation.id,
            correlation_id="test-123"
        )
    
    def test_routes_billing_query_to_order_agent(self, router, mock_openai):
        mock_openai.return_value.invoke.return_value = Mock(
            content='{"route": "order", "confidence": 0.9, "reasoning": "billing query"}'
        )
        
        result = router.process("What's my current subscription status?")
        
        assert result['route'] == 'order'
        assert result['confidence'] >= 0.7
    
    def test_routes_general_question_to_faq_agent(self, router, mock_openai):
        mock_openai.return_value.invoke.return_value = Mock(
            content='{"route": "faq", "confidence": 0.85, "reasoning": "general question"}'
        )
        
        result = router.process("How do I export my data?")
        
        assert result['route'] == 'faq'
    
    def test_fallback_routing_on_json_parse_error(self, router, mock_openai):
        mock_openai.return_value.invoke.return_value = Mock(
            content='Invalid response without JSON'
        )
        
        result = router.process("subscription billing payment")
        
        # Should fall back to keyword-based routing
        assert result['route'] == 'order'
```

**File:** `tests/unit/test_tools/test_db_lookup.py`

```python
import pytest
from apps.agents.tools.db_lookup import get_customer_info, get_subscription_details

class TestDbLookupTools:
    
    def test_get_customer_info_success(self, sample_customer):
        result = get_customer_info.invoke({"customer_email": sample_customer.email})
        
        assert "Test User" in result
        assert sample_customer.email in result
    
    def test_get_customer_info_not_found(self, db):
        result = get_customer_info.invoke({"customer_email": "nonexistent@example.com"})
        
        assert "No customer found" in result
    
    def test_get_subscription_details_no_subscriptions(self, sample_customer):
        result = get_subscription_details.invoke({"customer_email": sample_customer.email})
        
        assert "No subscriptions found" in result
```

**Dependencies to add:**
```
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
pytest-asyncio==0.21.1
factory-boy==3.3.0
```

---

### 2.2 Redis Caching for Memory

**File:** `apps/agents/memory.py` - Add caching layer

```python
from django.core.cache import cache
from django.conf import settings

class ConversationMemory:
    CACHE_TTL = 3600  # 1 hour
    
    def _get_cache_key(self) -> str:
        return f"conversation_memory:{self.conversation_id}"
    
    def get_context_messages(self, limit: int = None) -> list:
        """Get context messages with caching."""
        cache_key = self._get_cache_key()
        cached = cache.get(cache_key)
        
        if cached:
            messages = cached
        else:
            messages = self._load_messages_from_db()
            cache.set(cache_key, messages, self.CACHE_TTL)
        
        limit = limit or self.context_window_size
        return messages[-limit:]
    
    def add_message(self, role: str, content: str, **kwargs):
        """Add message and invalidate cache."""
        # ... existing logic ...
        
        # Invalidate cache
        cache.delete(self._get_cache_key())
    
    def _load_messages_from_db(self) -> list:
        """Load messages from database."""
        messages = Message.objects.filter(
            conversation=self.conversation
        ).order_by('created_at')
        
        return [
            {
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
            }
            for msg in messages
        ]
```

---

### 2.3 API Versioning

**File:** `config/urls.py`

```python
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='chat.html'), name='chat'),
    
    # API v1
    path('api/v1/', include('apps.support.urls')),
    
    # Keep legacy routes for backward compatibility (deprecate later)
    path('api/', include('apps.support.urls')),
]
```

---

### 2.4 Enhanced Error Handling

**File:** `apps/core/exceptions.py`

```python
"""
Custom exception handlers for the API.
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

class APIException(Exception):
    """Base API exception."""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_message = "An unexpected error occurred"
    
    def __init__(self, message=None, details=None):
        self.message = message or self.default_message
        self.details = details


class AgentProcessingError(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_message = "AI agent processing failed"


class RateLimitExceeded(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_message = "Rate limit exceeded"


class CustomerNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_message = "Customer not found"


def custom_exception_handler(exc, context):
    """Custom exception handler with logging."""
    response = exception_handler(exc, context)
    
    correlation_id = getattr(context.get('request'), 'correlation_id', 'unknown')
    
    if response is None:
        # Handle custom exceptions
        if isinstance(exc, APIException):
            logger.error(
                f"API Error: {exc.message}",
                extra={
                    'correlation_id': correlation_id,
                    'status_code': exc.status_code,
                    'details': exc.details,
                }
            )
            return Response(
                {
                    'error': exc.message,
                    'details': exc.details,
                    'correlation_id': correlation_id,
                },
                status=exc.status_code
            )
        
        # Unhandled exception
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={'correlation_id': correlation_id}
        )
        return Response(
            {
                'error': 'Internal server error',
                'correlation_id': correlation_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    # Add correlation ID to all error responses
    if response.data:
        response.data['correlation_id'] = correlation_id
    
    return response
```

---

## 🟢 Phase 3: Medium Priority (First Month)

### 3.1 WebSocket Support for Real-time Chat

**File:** `apps/support/consumers.py` (NEW FILE)

```python
"""
WebSocket consumer for real-time chat.
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.agents.orchestrator import AgentOrchestrator
from apps.core.models import Conversation

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
        self.room_group_name = f'chat_{self.conversation_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')
        customer_email = data.get('customer_email')
        
        # Send typing indicator
        await self.send(json.dumps({
            'type': 'typing',
            'status': True
        }))
        
        try:
            # Process message
            response = await self.process_message(message, customer_email)
            
            await self.send(json.dumps({
                'type': 'message',
                'content': response['content'],
                'agent_type': response['agent_type'],
                'tools_used': response.get('tools_used', []),
            }))
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.send(json.dumps({
                'type': 'error',
                'message': 'An error occurred processing your message'
            }))
        finally:
            await self.send(json.dumps({
                'type': 'typing',
                'status': False
            }))
    
    @database_sync_to_async
    def process_message(self, message: str, customer_email: str = None):
        orchestrator = AgentOrchestrator(
            conversation_id=self.conversation_id,
            customer_email=customer_email,
        )
        return orchestrator.process_message(message)
```

**Dependencies to add:**
```
channels==4.0.0
channels-redis==4.1.0
```

---

### 3.2 Prometheus Metrics

**File:** `apps/core/metrics.py` (NEW FILE)

```python
"""
Prometheus metrics for monitoring.
"""
from prometheus_client import Counter, Histogram, Gauge

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Agent metrics
agent_requests_total = Counter(
    'agent_requests_total',
    'Total agent requests',
    ['agent_type', 'status']
)

agent_processing_duration_seconds = Histogram(
    'agent_processing_duration_seconds',
    'Agent processing duration',
    ['agent_type'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

agent_tool_calls_total = Counter(
    'agent_tool_calls_total',
    'Total tool calls by agents',
    ['agent_type', 'tool_name', 'status']
)

# LLM metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'status']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['model', 'type']  # type: prompt, completion
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['model'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

# RAG metrics
vector_search_duration_seconds = Histogram(
    'vector_search_duration_seconds',
    'Vector search duration',
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Active conversations
active_conversations = Gauge(
    'active_conversations',
    'Number of active conversations'
)
```

**File:** `apps/core/middleware.py` - Add metrics middleware

```python
from apps.core.metrics import http_requests_total, http_request_duration_seconds

class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)
        
        return response
```

**Dependencies to add:**
```
prometheus-client==0.19.0
django-prometheus==2.3.1
```

---

### 3.3 OpenTelemetry Tracing

**File:** `apps/core/tracing.py` (NEW FILE)

```python
"""
OpenTelemetry tracing configuration.
"""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_tracing(service_name: str = "customer-support-agents"):
    """Initialize OpenTelemetry tracing."""
    resource = Resource.create({"service.name": service_name})
    
    provider = TracerProvider(resource=resource)
    
    # Configure exporter (Jaeger, Zipkin, etc.)
    exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"),
        insecure=True
    )
    
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    
    # Auto-instrument frameworks
    DjangoInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    CeleryInstrumentor().instrument()
    RedisInstrumentor().instrument()
    
    return trace.get_tracer(__name__)
```

**Dependencies to add:**
```
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-exporter-otlp==1.22.0
opentelemetry-instrumentation-django==0.43b0
opentelemetry-instrumentation-requests==0.43b0
opentelemetry-instrumentation-celery==0.43b0
opentelemetry-instrumentation-redis==0.43b0
```

---

### 3.4 LLM Cost Tracking

**File:** `apps/agents/cost_tracker.py` (NEW FILE)

```python
"""
LLM cost tracking and budgeting.
"""
import logging
from decimal import Decimal
from django.db import models
from django.conf import settings

logger = logging.getLogger(__name__)

# Pricing per 1K tokens (as of Dec 2024)
LLM_PRICING = {
    'gpt-4.1-mini': {
        'prompt': Decimal('0.00015'),
        'completion': Decimal('0.0006'),
    },
    'gpt-4-turbo': {
        'prompt': Decimal('0.01'),
        'completion': Decimal('0.03'),
    },
    'text-embedding-3-small': {
        'prompt': Decimal('0.00002'),
        'completion': Decimal('0'),
    },
}


class LLMUsage(models.Model):
    """Track LLM usage for cost analysis."""
    conversation_id = models.UUIDField(null=True, blank=True)
    model = models.CharField(max_length=50)
    prompt_tokens = models.IntegerField()
    completion_tokens = models.IntegerField()
    total_tokens = models.IntegerField()
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6)
    agent_type = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['model', 'created_at']),
            models.Index(fields=['conversation_id']),
        ]


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Calculate estimated cost for LLM usage."""
    pricing = LLM_PRICING.get(model, LLM_PRICING['gpt-4.1-mini'])
    
    prompt_cost = (Decimal(prompt_tokens) / 1000) * pricing['prompt']
    completion_cost = (Decimal(completion_tokens) / 1000) * pricing['completion']
    
    return prompt_cost + completion_cost


def track_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    conversation_id: str = None,
    agent_type: str = None
):
    """Track LLM usage and cost."""
    total_tokens = prompt_tokens + completion_tokens
    cost = calculate_cost(model, prompt_tokens, completion_tokens)
    
    LLMUsage.objects.create(
        conversation_id=conversation_id,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost=cost,
        agent_type=agent_type,
    )
    
    logger.info(
        f"LLM usage tracked: {model} - {total_tokens} tokens - ${cost:.6f}",
        extra={
            'model': model,
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'cost': float(cost),
        }
    )
    
    return cost
```

---

## 🔵 Phase 4: Optimization

### 4.1 Streaming Responses

**File:** `apps/agents/base.py` - Add streaming support

```python
from langchain_core.callbacks import StreamingStdOutCallbackHandler

class BaseAgent(ABC):
    def invoke_llm_streaming(self, messages: list):
        """Invoke LLM with streaming response."""
        streaming_llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
        )
        
        for chunk in streaming_llm.stream(messages):
            yield chunk.content
```

---

### 4.2 Parallel Tool Execution

**File:** `apps/agents/base.py` - Add async tool execution

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class BaseAgent(ABC):
    async def execute_tools_parallel(self, tool_calls: list) -> list:
        """Execute multiple tools in parallel."""
        with ThreadPoolExecutor(max_workers=5) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    executor,
                    self._execute_single_tool,
                    tool_call
                )
                for tool_call in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return results
    
    def _execute_single_tool(self, tool_call: dict) -> dict:
        """Execute a single tool and return result."""
        tool_name = tool_call['name']
        tool_args = tool_call['args']
        
        tool = self.get_tool_by_name(tool_name)
        if tool:
            result = tool.invoke(tool_args)
            return {'name': tool_name, 'result': result, 'success': True}
        
        return {'name': tool_name, 'result': None, 'success': False}
```

---

### 4.3 Query Optimization

**File:** `apps/support/views.py` - Optimize queries

```python
class ConversationViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Conversation.objects.select_related(
            'customer'
        ).prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.order_by('-created_at')[:10]
            )
        ).order_by('-updated_at')
```

**File:** `apps/agents/tools/db_lookup.py` - Optimize lookups

```python
@tool
def get_subscription_details(customer_email: str) -> str:
    """Get subscription details with optimized query."""
    try:
        customer = Customer.objects.select_related().get(
            email=customer_email.lower().strip()
        )
        subscriptions = Subscription.objects.filter(
            customer=customer
        ).select_related(
            'customer'
        ).order_by('-created_at')[:3]
        
        # ... rest of implementation
```

---

## 📋 Implementation Checklist

### Phase 1: Critical ✅
- [ ] Add authentication (JWT)
- [ ] Add rate limiting
- [ ] Add LLM timeout and retry logic
- [ ] Add database indexes
- [ ] Create production settings file
- [ ] Add HNSW vector index

### Phase 2: High Priority
- [ ] Create test directory structure
- [ ] Write unit tests for agents
- [ ] Write unit tests for tools
- [ ] Write integration tests
- [ ] Add Redis caching for memory
- [ ] Add API versioning
- [ ] Enhance error handling

### Phase 3: Medium Priority
- [ ] Add WebSocket support
- [ ] Add Prometheus metrics
- [ ] Add OpenTelemetry tracing
- [ ] Add LLM cost tracking
- [ ] Create monitoring dashboards

### Phase 4: Optimization
- [ ] Implement streaming responses
- [ ] Add parallel tool execution
- [ ] Optimize database queries
- [ ] Add connection pooling
- [ ] Performance benchmarking

---

## 📦 Updated Dependencies (requirements.txt additions)

```
# Authentication
djangorestframework-simplejwt==5.3.1

# Retry Logic
tenacity==8.2.3

# Testing
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
pytest-asyncio==0.21.1
factory-boy==3.3.0

# WebSockets
channels==4.0.0
channels-redis==4.1.0

# Monitoring
prometheus-client==0.19.0
django-prometheus==2.3.1

# Tracing
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-exporter-otlp==1.22.0
opentelemetry-instrumentation-django==0.43b0
opentelemetry-instrumentation-requests==0.43b0
opentelemetry-instrumentation-celery==0.43b0
opentelemetry-instrumentation-redis==0.43b0

# Caching
django-redis==5.4.0
```

---

## 🎯 Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| API Response Time (P99) | < 500ms | Prometheus histogram |
| Agent Processing Time | < 5s | Custom metrics |
| Error Rate | < 1% | Error counter |
| Test Coverage | > 80% | pytest-cov |
| Uptime | > 99.9% | Health checks |
| LLM Cost per Conversation | < $0.10 | Cost tracker |

---

**Last Updated:** December 2024  
**Next Review:** Before production deployment

