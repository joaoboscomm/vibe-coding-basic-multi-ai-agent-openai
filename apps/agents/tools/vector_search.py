"""
Vector search tool for FAQ and knowledge base queries using pgvector.
"""
import logging
import time
from typing import Optional

from django.conf import settings
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from pgvector.django import CosineDistance

from apps.core.middleware import AgentTracingMiddleware
from apps.core.models import KnowledgeDocument

logger = logging.getLogger(__name__)


def get_embeddings():
    """Get the OpenAI embeddings model."""
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )


def vector_search(
    query: str,
    top_k: int = 5,
    category: Optional[str] = None,
    correlation_id: str = '',
) -> list[dict]:
    """
    Perform vector similarity search on the knowledge base.
    
    Args:
        query: The search query
        top_k: Number of results to return
        category: Optional category filter
        correlation_id: Request correlation ID for tracing
        
    Returns:
        List of matching documents with scores
    """
    start_time = time.time()
    
    AgentTracingMiddleware.trace_tool_call(
        tool_name='vector_search',
        agent_type='faq',
        correlation_id=correlation_id,
        input_data={'query': query, 'top_k': top_k, 'category': category},
    )
    
    try:
        # Generate embedding for the query
        embeddings = get_embeddings()
        query_embedding = embeddings.embed_query(query)
        
        # Build the query
        queryset = KnowledgeDocument.objects.filter(
            is_active=True,
            embedding__isnull=False,
        )
        
        if category:
            queryset = queryset.filter(category=category)
        
        # Perform similarity search using pgvector
        results = queryset.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).order_by('distance')[:top_k]
        
        # Format results
        documents = []
        for doc in results:
            similarity = 1 - doc.distance  # Convert distance to similarity
            documents.append({
                'id': str(doc.id),
                'title': doc.title,
                'content': doc.content,
                'category': doc.category,
                'similarity': round(similarity, 4),
            })
        
        duration_ms = (time.time() - start_time) * 1000
        AgentTracingMiddleware.trace_tool_result(
            tool_name='vector_search',
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            success=True,
        )
        
        logger.info(
            f"Vector search completed: {len(documents)} results for query '{query[:50]}...'",
            extra={'correlation_id': correlation_id}
        )
        
        return documents
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        AgentTracingMiddleware.trace_tool_result(
            tool_name='vector_search',
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            success=False,
        )
        logger.error(f"Vector search failed: {e}", extra={'correlation_id': correlation_id})
        raise


@tool
def search_knowledge_base(query: str, category: str = None) -> str:
    """
    Search the knowledge base for relevant documentation and FAQs.
    Use this tool to find information about CloudFlow features, how-to guides,
    policies, and troubleshooting steps.
    
    Args:
        query: The search query describing what information you need
        category: Optional filter for document category (faq, documentation, policy, troubleshooting)
        
    Returns:
        A formatted string with the most relevant knowledge base articles
    """
    results = vector_search(query=query, top_k=3, category=category)
    
    if not results:
        return "No relevant information found in the knowledge base."
    
    formatted_results = []
    for i, doc in enumerate(results, 1):
        formatted_results.append(
            f"**Result {i}** (Relevance: {doc['similarity']:.0%})\n"
            f"Title: {doc['title']}\n"
            f"Category: {doc['category']}\n"
            f"Content: {doc['content']}\n"
        )
    
    return "\n---\n".join(formatted_results)

