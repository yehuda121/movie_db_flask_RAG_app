"""Build strict RAG prompts so the LLM uses retrieved context correctly."""

SYSTEM_PROMPT = """You are a movie database assistant.

Rules:
1. Answer ONLY using the MOVIE RECORDS in the user message. Do not use outside knowledge.
2. If the records contain the answer, you MUST answer clearly and completely.
3. For "which movies" or "movies that include/feature" questions: list EVERY movie title from the records where the person, director, or keyword appears in Title, Director, or Main Cast (Actors) fields.
4. Main Cast lists four actors — if a name appears there, that movie counts.
5. Only say you do not have enough information when the records truly do not contain anything relevant to the question.
6. Do not invent movies, people, or facts not present in the records."""


def format_chunk_for_prompt(chunk, index):
    """Format one movie chunk so actors and credits are easy for the model to read."""
    text = chunk.get("text", "")
    title = chunk.get("title", "Unknown")

    # Prefer structured text from indexing; wrap with clear record boundaries
    return (
        f"=== MOVIE RECORD {index} ===\n"
        f"Title: {title}\n"
        f"{text}\n"
        f"=== END MOVIE RECORD {index} ==="
    )


def build_rag_messages(question, context_chunks, emphasis=False):
    """
    Build system + user messages for Groq.
    Returns (messages_list, full_prompt_text_for_debug).
    """
    formatted_records = [
        format_chunk_for_prompt(chunk, i) for i, chunk in enumerate(context_chunks, start=1)
    ]
    context_block = "\n\n".join(formatted_records)

    task_hints = (
        "Read all MOVIE RECORDS above. "
        "If the question asks which movies include a person, check the "
        "'Main Cast (Actors)' and 'Director' lines in each record."
    )
    if emphasis:
        task_hints += (
            " The records DO contain relevant information — "
            "answer using the movie titles and fields shown. Do not refuse."
        )

    user_content = (
        f"MOVIE RECORDS FROM DATABASE (use only these):\n\n"
        f"{context_block}\n\n"
        f"---\n"
        f"{task_hints}\n\n"
        f"Question: {question}\n\n"
        f"Answer (be specific; list movie titles when applicable):"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    debug_text = (
        f"[SYSTEM]\n{SYSTEM_PROMPT}\n\n"
        f"[USER]\n{user_content}"
    )
    return messages, debug_text


# Kept for backward compatibility if anything still calls build_rag_prompt
def build_rag_prompt(question, context_chunks):
    """Legacy single-string prompt (prefer build_rag_messages)."""
    _, debug_text = build_rag_messages(question, context_chunks)
    return debug_text
