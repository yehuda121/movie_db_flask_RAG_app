# MovieDB – Flask + SQLite Movie Database

A professional beginner-friendly movie database web application built with Flask, SQLite, HTML, CSS, and Docker.

The project simulates a simplified IMDB-style platform where users can browse movies, view movie details, and leave reviews, while an admin user can manage movie content and upload posters.

---

# Features

* Flask web application
* SQLite local database
* Docker support with persistent volumes
* Movie poster gallery homepage
* Movie details pages
* Movie reviews system
* Search movies by title
* Movies sorted by rating popularity
* Admin login and movie management
* Image upload support
* Responsive dark-themed UI
* Persistent database and uploaded posters using Docker volumes
* **Ask AI** RAG page (FAISS + local embeddings + Groq LLM)

---

# Technologies

| Technology | Purpose                      |
| ---------- | ---------------------------- |
| Python     | Backend programming language |
| Flask      | Web framework                |
| SQLite     | Local database               |
| HTML / CSS | Frontend UI                  |
| Docker     | Containerization             |
| Jinja2     | Flask templating engine      |
| FAISS      | Vector search index          |
| sentence-transformers | Local embeddings  |
| Groq       | LLM API for answers          |

---

# Project Structure

```text
project_1/
│
├── docker-compose.yml
│
└── movie_flask_app/
    │
    ├── app.py
    ├── requirements.txt
    ├── Dockerfile
    ├── .dockerignore
    │
    ├── data/
    │   ├── database.db
    │   └── faiss/
    │
    ├── rag/
    │   ├── embedding_service.py
    │   ├── faiss_index.py
    │   ├── retrieval.py
    │   ├── prompt_builder.py
    │   └── llm_service.py
    │
    ├── database/
    │   ├── db.py
    │   └── seed.py
    │
    ├── templates/
    │
    └── static/
        ├── css/
        └── images/
```

---

# Admin Credentials

| Username | Password |
| -------- | -------- |
| admin    | admin123 |

---

# Run with Docker (Recommended)

From the `project_1` folder:

```powershell
docker compose up --build
```

Open the application:

```text
http://localhost:5000
```

Stop the containers:

```powershell
docker compose down
```

---

# Docker Volume Persistence

The project uses Docker bind mounts to persist:

* SQLite database
* Uploaded movie posters

Persistent folders:

```text
movie_flask_app/data
movie_flask_app/static/images/posters
```

This means your data remains saved even if the container is removed or rebuilt.

---

# Environment Variables

| Variable      | Description                               |
| ------------- | ----------------------------------------- |
| FLASK_DEBUG   | Enables/disables debug mode               |
| SECRET_KEY    | Flask session secret                      |
| DATABASE_PATH | SQLite database path inside the container |
| GROQ_API_KEY  | Groq API key (set in `.env`, not in Git)  |

---

# Run Locally (Without Docker)

## 1. Enter the application folder

```powershell
cd movie_flask_app
```

## 2. Create virtual environment

```powershell
python -m venv venv
```

## 3. Activate virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

## 4. Install dependencies

```powershell
pip install -r requirements.txt
```

## 5. Seed example movies

```powershell
python database\seed.py
```

## 6. Run the Flask server

```powershell
python app.py
```

Open:

```text
http://localhost:5000
```

---

# Verify Database Persistence

1. Start the application using Docker
2. Add a new movie or review
3. Stop the containers

```powershell
docker compose down
```

4. Start the containers again

```powershell
docker compose up
```

5. Verify that:

* movies still exist
* reviews still exist
* uploaded posters still exist

You can also verify that:

```text
movie_flask_app/data/database.db
```

was updated on your Windows machine.

---

# Security Notes

This project is intended for learning purposes.

The following simplifications were intentionally used:

* Hardcoded admin credentials
* SQLite local database
* Flask debug mode during development

These should be improved for real production deployments.

---

# RAG (Ask AI) Feature

The **Ask AI** page (`/ask`) answers questions using **Retrieval-Augmented Generation (RAG)** over your SQLite movie data.

## How it works

| Step | Component | Description |
| ---- | --------- | ----------- |
| 1 | **SQLite** | Source of truth for movies and reviews |
| 2 | **Chunking** | One text chunk per movie (title, plot, director, actors, year, reviews) |
| 3 | **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (runs locally) |
| 4 | **FAISS** | Vector index stored in `data/faiss/` |
| 5 | **Retrieval** | Top similar chunks above a similarity threshold |
| 6 | **Groq LLM** | Generates an answer using **only** retrieved context |

If nothing relevant is found, the app returns:

> I could not find enough relevant information in the movie knowledge base to answer this question.

## Environment variables

Create `movie_flask_app/.env` (copy from `.env.example`). **Do not commit `.env` to Git.**

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `GROQ_API_KEY` | Yes (for Ask AI) | Your Groq API key |
| `GROQ_MODEL` | No | Default: `llama-3.1-8b-instant` |
| `RAG_SIMILARITY_THRESHOLD` | No | Default: `0.35` |
| `RAG_TOP_K` | No | Default: `3` |
| `RAG_DEBUG` | No | Set to `1` to log chunks, scores, and prompts to the console |

After changing chunk format, **rebuild the RAG index** so actor fields use the new layout.

## Rebuild the RAG index

The index must match your SQLite data.

**Automatic:** Rebuilds after adding a movie (admin).

**Manual:** Admin Dashboard → **Rebuild RAG Index** (also use after adding new reviews)

**Command line:**

```powershell
cd movie_flask_app
python -c "from rag.faiss_index import rebuild_rag_index; print(rebuild_rag_index(), 'movies indexed')"
```

## Run with Docker (RAG)

From `project_1`:

```powershell
docker compose up --build
```

Ensure `movie_flask_app/.env` contains `GROQ_API_KEY`. Docker loads it via `env_file`.

FAISS files persist in `movie_flask_app/data/faiss/` (same volume as the database).

First startup may take several minutes while the embedding model downloads.

## Example questions and expected behavior

| Question | Expected behavior |
| -------- | ----------------- |
| "Who directed Inception?" | Retrieves *Inception* chunk; answers from context |
| "Which movies has Christopher Nolan directed?" | Retrieves Nolan movies if in DB |
| "What reviews does The Matrix have?" | Uses review text from that movie's chunk |
| "What is the weather in Paris?" | No relevant chunks → safe “not enough information” message |
| "Tell me about movie xyz123" | Unknown title → threshold not met or empty retrieval |

## RAG code structure

```text
rag/
├── embedding_service.py   # Local embeddings
├── faiss_index.py         # Build / save / load FAISS
├── retrieval.py           # Search + full ask pipeline
├── prompt_builder.py      # Strict context-only prompt
└── llm_service.py         # Groq API calls
```

---

# Future Improvements

* User authentication system
* Movie categories and genres
* Pagination
* Better review moderation
* Cloud database support
* AWS or cloud deployment
* CI/CD pipeline
* Production-ready Gunicorn setup
* Unit and integration tests

---

# Author

Yehuda Shmulevitz
Software Engineering Graduate
