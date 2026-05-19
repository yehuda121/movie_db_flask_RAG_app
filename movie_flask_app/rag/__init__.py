"""RAG package: embeddings, FAISS index, retrieval, and Groq LLM."""

from rag.faiss_index import index_exists, rebuild_rag_index

__all__ = ["index_exists", "rebuild_rag_index"]
