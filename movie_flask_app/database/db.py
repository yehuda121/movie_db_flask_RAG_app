"""SQLite database connection and helper functions."""

import os
import sqlite3

# Project root (movie_flask_app/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Allow Docker Compose to override the DB path; default is data/database.db
DATABASE_PATH = os.environ.get(
    "DATABASE_PATH",
    os.path.join(BASE_DIR, "data", "database.db"),
)


def get_db_connection():
    """Open a connection to the SQLite database file."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_movies_table(conn):
    """Create the movies table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            director TEXT NOT NULL,
            actor_1 TEXT NOT NULL,
            actor_2 TEXT NOT NULL,
            actor_3 TEXT NOT NULL,
            actor_4 TEXT NOT NULL,
            release_year INTEGER NOT NULL,
            poster_filename TEXT NOT NULL
        )
        """
    )


def create_reviews_table(conn):
    """Create the reviews table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            reviewer_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            review_text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(movie_id) REFERENCES movies(id)
        )
        """
    )


def init_db():
    """Initialize database tables."""
    conn = get_db_connection()
    create_movies_table(conn)
    create_reviews_table(conn)
    conn.commit()
    conn.close()


def get_all_movies():
    """Return all movies ordered by title (used on admin dashboard)."""
    conn = get_db_connection()
    movies = conn.execute(
        "SELECT * FROM movies ORDER BY title ASC"
    ).fetchall()
    conn.close()
    return movies


def get_popular_movies(search_term=""):
    """
    Return movies for the homepage, sorted by popularity.

    Popularity = average review rating (highest first).
    Movies with no reviews are listed last.
    Optional search_term filters titles (partial match, case-insensitive).
    """
    conn = get_db_connection()
    search_term = search_term.strip()

    # Base query: join movies with reviews and compute average rating
    query = """
        SELECT
            m.*,
            COALESCE(AVG(r.rating), 0) AS avg_rating,
            COUNT(r.id) AS review_count
        FROM movies m
        LEFT JOIN reviews r ON r.movie_id = m.id
    """
    params = []

    # Safe partial search — user input only goes into ? placeholders
    if search_term:
        query += " WHERE LOWER(m.title) LIKE ? "
        params.append(f"%{search_term.lower()}%")

    query += """
        GROUP BY m.id
        ORDER BY
            (COUNT(r.id) > 0) DESC,
            avg_rating DESC,
            m.title ASC
    """

    movies = conn.execute(query, params).fetchall()
    conn.close()
    return movies


def get_movie_by_slug(slug):
    """Return one movie row by slug, or None if not found."""
    conn = get_db_connection()
    movie = conn.execute(
        "SELECT * FROM movies WHERE slug = ?",
        (slug,),
    ).fetchone()
    conn.close()
    return movie


def get_reviews_for_movie(movie_id):
    """Return all reviews for a movie, newest first."""
    conn = get_db_connection()
    reviews = conn.execute(
        """
        SELECT * FROM reviews
        WHERE movie_id = ?
        ORDER BY created_at DESC
        """,
        (movie_id,),
    ).fetchall()
    conn.close()
    return reviews


def insert_review(movie_id, reviewer_name, rating, review_text):
    """Insert a new review for a movie."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO reviews (movie_id, reviewer_name, rating, review_text)
        VALUES (?, ?, ?, ?)
        """,
        (movie_id, reviewer_name, rating, review_text),
    )
    conn.commit()
    conn.close()


def insert_movie(
    title,
    slug,
    description,
    director,
    actor_1,
    actor_2,
    actor_3,
    actor_4,
    release_year,
    poster_filename,
):
    """Insert a new movie into the database."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO movies (
            title, slug, description, director,
            actor_1, actor_2, actor_3, actor_4,
            release_year, poster_filename
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            slug,
            description,
            director,
            actor_1,
            actor_2,
            actor_3,
            actor_4,
            release_year,
            poster_filename,
        ),
    )
    conn.commit()
    conn.close()


def slug_exists(slug):
    """Check whether a movie slug is already in use."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id FROM movies WHERE slug = ?",
        (slug,),
    ).fetchone()
    conn.close()
    return row is not None
