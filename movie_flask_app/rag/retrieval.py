"""Retrieve relevant movie chunks and run the full RAG question flow."""

import logging
import os

from rag.embedding_service import embed_query
from rag.faiss_index import index_exists, load_index, rebuild_rag_index
from rag.llm_service import generate_answer_from_messages
from rag.prompt_builder import build_rag_messages

# Minimum cosine similarity to use a chunk as context or show in the UI
MIN_CONTEXT_SCORE = float(os.environ.get("RAG_MIN_CONTEXT_SCORE", "0.40"))

TOP_K = int(os.environ.get("RAG_TOP_K", "3"))

NO_CONTEXT_MESSAGE = (
    "I could not find enough relevant information in the movie knowledge base "
    "to answer this question."
)

# Only used when retrieval returns zero chunks (not when the LLM refuses)
RAG_DEBUG = os.environ.get("RAG_DEBUG", "0") == "1"

logger = logging.getLogger("rag")
if RAG_DEBUG:
    logging.basicConfig(level=logging.INFO)


def _debug_log(message):
    if RAG_DEBUG:
        logger.info(message)


# Phrases that suggest the model refused despite having context
_LLM_REFUSAL_PATTERNS = [
    "not enough information",
    "do not have enough",
    "don't have enough",
    "cannot answer",
    "can't answer",
    "no information",
    "not in the context",
    "not in the provided",
    "i do not know",
    "i don't know",
]


def _retrieval_params_for_question(question):
    """
    Use broader retrieval for list/cast questions (e.g. 'which movies include X').
    """
    q = question.lower()
    list_keywords = (
        "which movies",
        "what movies",
        "movies include",
        "movies feature",
        "movies with",
        "movies starring",
        "movies did",
        "starred in",
        "appear in",
        "actor",
        "actress",
        "cast",
    )
    if any(keyword in q for keyword in list_keywords):
        return max(TOP_K, 8)
    return TOP_K


def _looks_like_unjustified_refusal(answer):
    """True when the model declined but we had retrieved sources."""
    text = answer.lower()
    return any(pattern in text for pattern in _LLM_REFUSAL_PATTERNS)


def retrieve_relevant_chunks(question, top_k=None, min_score=None):
    """
    Search FAISS for chunks similar to the question.
    Returns only chunks with similarity score >= min_score (default 0.40).
    """
    top_k = top_k or _retrieval_params_for_question(question)
    min_score = min_score if min_score is not None else MIN_CONTEXT_SCORE

    if not index_exists():
        return []

    faiss_index, metadata = load_index()
    chunks = metadata.get("chunks", [])
    if not chunks or faiss_index.ntotal == 0:
        return []

    query_vector = embed_query(question).reshape(1, -1)
    search_k = min(top_k, faiss_index.ntotal)
    scores, indices = faiss_index.search(query_vector, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        similarity = float(score)
        if similarity < min_score:
            continue

        chunk = chunks[int(idx)]
        results.append(
            {
                "movie_id": chunk["movie_id"],
                "title": chunk["title"],
                "slug": chunk["slug"],
                "text": chunk["text"],
                "score": round(similarity, 4),
            }
        )

    _debug_log(
        f"Retrieved {len(results)} chunk(s) with score >= {min_score} for: {question!r}"
    )
    for item in results:
        _debug_log(f"  - {item['title']} (score={item['score']})")

    return results


def _generate_with_context(question, sources, emphasis=False):
    """Call Groq with structured messages; return (answer, prompt_debug_text)."""
    messages, prompt_debug = build_rag_messages(question, sources, emphasis=emphasis)
    _debug_log("--- Prompt sent to Groq ---")
    _debug_log(prompt_debug)
    _debug_log("--- End prompt ---")

    answer = generate_answer_from_messages(messages)
    return answer, prompt_debug


MAX_QUESTION_LENGTH = 150


def ask_question(question):
    """
    Full RAG pipeline: retrieve → prompt → Groq.
    Returns a dict with keys: success, answer, sources, error.
    """
    question = question.strip()
    if not question:
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "error": "Please enter a question.",
            "clear_input": False,
        }
    if len(question) > MAX_QUESTION_LENGTH:
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "error": "Question is too long. Maximum length is 150 characters.",
            "clear_input": False,
        }

    try:
        sources = retrieve_relevant_chunks(question)
    except FileNotFoundError as error:
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "error": str(error),
            "clear_input": False,
        }
    except Exception as error:
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "error": f"Retrieval failed: {error}",
            "clear_input": False,
        }

    # No Groq call unless at least one chunk scores >= MIN_CONTEXT_SCORE
    if not sources:
        _debug_log(
            f"No chunks with score >= {MIN_CONTEXT_SCORE} — "
            "skipping Groq and returning retrieval fallback."
        )
        return {
            "success": True,
            "answer": NO_CONTEXT_MESSAGE,
            "sources": [],
            "error": None,
            "clear_input": True,
            "show_retrieval_section": True,
        }

    try:
        answer, _ = _generate_with_context(question, sources, emphasis=False)

        # One retry if the model refused despite relevant retrieved records
        if _looks_like_unjustified_refusal(answer):
            _debug_log("LLM refusal detected with sources present — retrying with emphasis.")
            answer, _ = _generate_with_context(question, sources, emphasis=True)

    except ValueError as error:
        return {
            "success": False,
            "answer": "",
            "sources": sources,
            "error": str(error),
            "clear_input": False,
            "show_retrieval_section": bool(sources),
        }
    except Exception as error:
        return {
            "success": False,
            "answer": "",
            "sources": sources,
            "error": f"LLM request failed: {error}",
            "clear_input": False,
            "show_retrieval_section": bool(sources),
        }

    return {
        "success": True,
        "answer": answer,
        "sources": sources,
        "error": None,
        "clear_input": True,
        "show_retrieval_section": True,
    }


def ensure_rag_index():
    """Build the index automatically if it does not exist yet."""
    if not index_exists():
        rebuild_rag_index()
