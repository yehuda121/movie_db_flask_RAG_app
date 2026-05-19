"""Build, save, and load the FAISS vector index and chunk metadata."""

import json
import os

import faiss
import numpy as np

from database.db import get_all_movies, get_reviews_for_movie
from rag.embedding_service import MODEL_NAME, embed_texts

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAISS_DIR = os.environ.get(
    "FAISS_DIR",
    os.path.join(BASE_DIR, "data", "faiss"),
)
INDEX_PATH = os.path.join(FAISS_DIR, "movies.index")
METADATA_PATH = os.path.join(FAISS_DIR, "metadata.json")


def build_movie_chunk(movie, reviews):
    """Convert one movie (and its reviews) into a single searchable text chunk."""
    lines = [
        f"Title: {movie['title']}",
        f"Release Year: {movie['release_year']}",
        f"Director: {movie['director']}",
        "Main Cast (Actors):",
        f"  - {movie['actor_1']}",
        f"  - {movie['actor_2']}",
        f"  - {movie['actor_3']}",
        f"  - {movie['actor_4']}",
        f"Plot Description: {movie['description']}",
    ]

    if reviews:
        lines.append("Reviews:")
        for review in reviews:
            lines.append(
                f"- {review['reviewer_name']} ({review['rating']}/5): {review['review_text']}"
            )
    else:
        lines.append("Reviews: No reviews yet.")

    return "\n".join(lines)


def load_chunks_from_database():
    """Load all movies from SQLite and build one text chunk per movie."""
    movies = get_all_movies()
    chunks = []

    for movie in movies:
        reviews = get_reviews_for_movie(movie["id"])
        chunks.append(
            {
                "movie_id": movie["id"],
                "title": movie["title"],
                "slug": movie["slug"],
                "text": build_movie_chunk(movie, reviews),
            }
        )

    return chunks


def index_exists():
    """Return True if both FAISS index and metadata files exist."""
    return os.path.isfile(INDEX_PATH) and os.path.isfile(METADATA_PATH)


def save_index(faiss_index, metadata):
    """Persist FAISS index and JSON metadata to data/faiss/."""
    os.makedirs(FAISS_DIR, exist_ok=True)
    faiss.write_index(faiss_index, INDEX_PATH)

    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)


def load_index():
    """Load FAISS index and metadata from disk."""
    if not index_exists():
        raise FileNotFoundError(
            "RAG index not found. Build it from the admin dashboard or add movies."
        )

    faiss_index = faiss.read_index(INDEX_PATH)
    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    return faiss_index, metadata


def rebuild_rag_index():
    """
    Rebuild the full FAISS index from all movies in SQLite.
    Returns the number of chunks indexed.
    """
    chunks = load_chunks_from_database()
    os.makedirs(FAISS_DIR, exist_ok=True)

    if not chunks:
        # Empty index placeholder
        metadata = {
            "model_name": MODEL_NAME,
            "chunk_count": 0,
            "chunks": [],
        }
        empty_index = faiss.IndexFlatIP(384)
        save_index(empty_index, metadata)
        return 0

    texts = [chunk["text"] for chunk in chunks]
    vectors = embed_texts(texts)

    dimension = vectors.shape[1]
    faiss_index = faiss.IndexFlatIP(dimension)
    faiss_index.add(vectors)

    metadata = {
        "model_name": MODEL_NAME,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    save_index(faiss_index, metadata)
    return len(chunks)
