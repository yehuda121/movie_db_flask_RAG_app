"""Call the Groq API to generate answers from the RAG prompt."""

import os

from groq import Groq

DEFAULT_MODEL = "llama-3.1-8b-instant"


def get_groq_client():
    """Create a Groq client using the API key from the environment."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your .env file or environment variables."
        )
    return Groq(api_key=api_key)


def generate_answer_from_messages(messages):
    """Send system + user messages to Groq and return the model text response."""
    client = get_groq_client()
    response = client.chat.completions.create(
        model=os.environ.get("GROQ_MODEL", DEFAULT_MODEL),
        messages=messages,
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()


def generate_answer(prompt):
    """Legacy: single user message (prefer generate_answer_from_messages)."""
    return generate_answer_from_messages(
        [{"role": "user", "content": prompt}]
    )
