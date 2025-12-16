"""
Knowledge base management for RAG system.
Handles document ingestion, embedding generation, and retrieval.
"""
import logging
from typing import Optional
from uuid import UUID

from django.db import transaction
from pgvector.django import CosineDistance

from apps.core.models import KnowledgeDocument
from .embeddings import get_embeddings_manager

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Manages the knowledge base for the RAG system.
    Handles document CRUD operations and embedding management.
    """

    def __init__(self):
        self.embeddings = get_embeddings_manager()

    def add_document(
        self,
        title: str,
        content: str,
        category: str = 'faq',
        metadata: dict = None,
    ) -> KnowledgeDocument:
        """
        Add a new document to the knowledge base with embedding.
        
        Args:
            title: Document title
            content: Document content
            category: Document category (faq, documentation, policy, troubleshooting)
            metadata: Optional metadata dictionary
            
        Returns:
            The created KnowledgeDocument instance
        """
        # Generate embedding for the content
        # Combine title and content for better semantic representation
        text_to_embed = f"{title}\n\n{content}"
        embedding = self.embeddings.embed_text(text_to_embed)
        
        # Create the document
        document = KnowledgeDocument.objects.create(
            title=title,
            content=content,
            category=category,
            embedding=embedding,
            metadata=metadata or {},
            is_active=True,
        )
        
        logger.info(f"Added document to knowledge base: {title}")
        return document

    def add_documents_batch(
        self,
        documents: list[dict],
    ) -> list[KnowledgeDocument]:
        """
        Add multiple documents to the knowledge base.
        
        Args:
            documents: List of document dictionaries with title, content, category, metadata
            
        Returns:
            List of created KnowledgeDocument instances
        """
        # Prepare texts for batch embedding
        texts = [f"{doc['title']}\n\n{doc['content']}" for doc in documents]
        embeddings = self.embeddings.embed_texts(texts)
        
        # Create documents in a transaction
        created_docs = []
        with transaction.atomic():
            for doc, embedding in zip(documents, embeddings):
                knowledge_doc = KnowledgeDocument.objects.create(
                    title=doc['title'],
                    content=doc['content'],
                    category=doc.get('category', 'faq'),
                    embedding=embedding,
                    metadata=doc.get('metadata', {}),
                    is_active=True,
                )
                created_docs.append(knowledge_doc)
        
        logger.info(f"Added {len(created_docs)} documents to knowledge base")
        return created_docs

    def update_document(
        self,
        document_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> KnowledgeDocument:
        """
        Update an existing document and regenerate embedding if content changes.
        
        Args:
            document_id: The document's UUID
            title: Optional new title
            content: Optional new content
            category: Optional new category
            metadata: Optional new metadata
            
        Returns:
            The updated KnowledgeDocument instance
        """
        document = KnowledgeDocument.objects.get(id=document_id)
        
        # Track if we need to regenerate embedding
        regenerate_embedding = False
        
        if title is not None:
            document.title = title
            regenerate_embedding = True
            
        if content is not None:
            document.content = content
            regenerate_embedding = True
            
        if category is not None:
            document.category = category
            
        if metadata is not None:
            document.metadata = metadata
        
        # Regenerate embedding if title or content changed
        if regenerate_embedding:
            text_to_embed = f"{document.title}\n\n{document.content}"
            document.embedding = self.embeddings.embed_text(text_to_embed)
        
        document.save()
        logger.info(f"Updated document: {document_id}")
        return document

    def delete_document(self, document_id: UUID) -> bool:
        """
        Soft delete a document (set is_active to False).
        
        Args:
            document_id: The document's UUID
            
        Returns:
            True if successful
        """
        try:
            document = KnowledgeDocument.objects.get(id=document_id)
            document.is_active = False
            document.save(update_fields=['is_active', 'updated_at'])
            logger.info(f"Soft deleted document: {document_id}")
            return True
        except KnowledgeDocument.DoesNotExist:
            logger.warning(f"Document not found for deletion: {document_id}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        min_similarity: float = 0.5,
    ) -> list[dict]:
        """
        Search the knowledge base using semantic similarity.
        
        Args:
            query: The search query
            top_k: Maximum number of results
            category: Optional category filter
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of matching documents with similarity scores
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        # Build query
        queryset = KnowledgeDocument.objects.filter(
            is_active=True,
            embedding__isnull=False,
        )
        
        if category:
            queryset = queryset.filter(category=category)
        
        # Search with cosine distance
        results = queryset.annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).order_by('distance')[:top_k]
        
        # Convert to list with similarity scores
        documents = []
        for doc in results:
            similarity = 1 - doc.distance
            
            # Apply similarity threshold
            if similarity >= min_similarity:
                documents.append({
                    'id': str(doc.id),
                    'title': doc.title,
                    'content': doc.content,
                    'category': doc.category,
                    'similarity': round(similarity, 4),
                    'metadata': doc.metadata,
                })
        
        logger.debug(f"Knowledge base search returned {len(documents)} results")
        return documents

    def get_document(self, document_id: UUID) -> Optional[KnowledgeDocument]:
        """Get a document by ID."""
        try:
            return KnowledgeDocument.objects.get(id=document_id, is_active=True)
        except KnowledgeDocument.DoesNotExist:
            return None

    def get_all_documents(
        self,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[KnowledgeDocument]:
        """Get all active documents, optionally filtered by category."""
        queryset = KnowledgeDocument.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        return list(queryset.order_by('-created_at')[:limit])

    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        total = KnowledgeDocument.objects.filter(is_active=True).count()
        by_category = {}
        
        for category in ['faq', 'documentation', 'policy', 'troubleshooting']:
            by_category[category] = KnowledgeDocument.objects.filter(
                is_active=True,
                category=category
            ).count()
        
        return {
            'total_documents': total,
            'by_category': by_category,
        }

