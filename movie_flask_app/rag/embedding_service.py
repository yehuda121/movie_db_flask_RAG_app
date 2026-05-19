"""Load the embedding model and convert text into vectors."""

import os

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Lazy-loaded model (downloaded on first use)
_embedding_model = None


def get_embedding_model():
    """Load the SentenceTransformer model once and reuse it."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        cache_dir = os.environ.get(
            "SENTENCE_TRANSFORMERS_HOME",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "models"),
        )
        os.makedirs(cache_dir, exist_ok=True)
        _embedding_model = SentenceTransformer(MODEL_NAME, cache_folder=cache_dir)
    return _embedding_model


def embed_texts(texts):
    """
    Create normalized embedding vectors for a list of text chunks.
    Normalization allows cosine similarity via inner product in FAISS.
    """
    if not texts:
        return np.array([]).reshape(0, 384)

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(vectors, dtype=np.float32)


def embed_query(question):
    """Embed a single user question."""
    vectors = embed_texts([question])
    return vectors[0]
