"""
Embeddings management for RAG system using OpenAI.
"""
import logging
from typing import Optional

from django.conf import settings
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class EmbeddingsManager:
    """
    Manages text embeddings using OpenAI's embedding models.
    Used for generating vector representations of documents and queries.
    """
    
    _instance: Optional['EmbeddingsManager'] = None
    _embeddings: Optional[OpenAIEmbeddings] = None

    def __new__(cls):
        """Singleton pattern for embeddings manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            logger.info(f"Initialized embeddings with model: {settings.EMBEDDING_MODEL}")

    @property
    def model(self) -> OpenAIEmbeddings:
        """Get the embeddings model."""
        return self._embeddings

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: The text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            embedding = self._embeddings.embed_query(text)
            logger.debug(f"Generated embedding for text: {text[:50]}...")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = self._embeddings.embed_documents(texts)
            logger.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    def get_dimensions(self) -> int:
        """Get the embedding dimensions."""
        return settings.EMBEDDING_DIMENSIONS


# Convenience function
def get_embeddings_manager() -> EmbeddingsManager:
    """Get the singleton embeddings manager instance."""
    return EmbeddingsManager()

