"""Seed the database with example movies for learning and demo."""

import os
import shutil
import struct
import zlib

from database.db import BASE_DIR, get_db_connection, init_db, insert_movie, slug_exists

POSTER_DIR = os.path.join(BASE_DIR, "static", "images", "posters")


def _create_simple_png(path, width, height, rgb):
    """Create a minimal solid-color PNG (no external dependencies)."""

    def chunk(chunk_type, data):
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw_rows = []
    for _ in range(height):
        row = b"\x00" + bytes(rgb) * width
        raw_rows.append(row)
    compressed = zlib.compress(b"".join(raw_rows), level=9)
    png_data = (
        signature
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    with open(path, "wb") as file:
        file.write(png_data)


def _ensure_poster(filename, color):
    """Create poster file if it does not exist yet."""
    os.makedirs(POSTER_DIR, exist_ok=True)
    path = os.path.join(POSTER_DIR, filename)
    if not os.path.exists(path):
        _create_simple_png(path, 400, 600, color)
    return filename


# Placeholder colors when repairing missing poster files
_POSTER_COLORS = [
    (30, 58, 95),
    (20, 20, 24),
    (72, 52, 88),
    (12, 92, 72),
    (120, 48, 48),
    (48, 88, 120),
    (55, 42, 68),
    (28, 68, 48),
]


def ensure_posters_from_database():
    """Create placeholder poster images for any movie missing a file on disk."""
    os.makedirs(POSTER_DIR, exist_ok=True)
    conn = get_db_connection()
    rows = conn.execute("SELECT poster_filename FROM movies").fetchall()
    conn.close()

    for index, row in enumerate(rows):
        filename = row["poster_filename"]
        path = os.path.join(POSTER_DIR, filename)
        if not os.path.exists(path):
            color = _POSTER_COLORS[index % len(_POSTER_COLORS)]
            _create_simple_png(path, 400, 600, color)


def seed_movies():
    """Insert example movies when the database is empty."""
    init_db()
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) AS total FROM movies").fetchone()["total"]
    conn.close()

    if count > 0:
        print("Database already has movies. Skipping seed.")
        return

    sample_movies = [
        {
            "title": "Inception",
            "slug": "inception",
            "description": "A thief who steals secrets through dreams is offered a chance at redemption.",
            "director": "Christopher Nolan",
            "actor_1": "Leonardo DiCaprio",
            "actor_2": "Joseph Gordon-Levitt",
            "actor_3": "Elliot Page",
            "actor_4": "Tom Hardy",
            "release_year": 2010,
            "poster": "inception.png",
            "color": (30, 58, 95),
        },
        {
            "title": "The Dark Knight",
            "slug": "the-dark-knight",
            "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into chaos.",
            "director": "Christopher Nolan",
            "actor_1": "Christian Bale",
            "actor_2": "Heath Ledger",
            "actor_3": "Aaron Eckhart",
            "actor_4": "Michael Caine",
            "release_year": 2008,
            "poster": "the-dark-knight.png",
            "color": (20, 20, 24),
        },
        {
            "title": "Interstellar",
            "slug": "interstellar",
            "description": "Explorers travel through a wormhole in space to ensure humanity's survival.",
            "director": "Christopher Nolan",
            "actor_1": "Matthew McConaughey",
            "actor_2": "Anne Hathaway",
            "actor_3": "Jessica Chastain",
            "actor_4": "Michael Caine",
            "release_year": 2014,
            "poster": "interstellar.png",
            "color": (72, 52, 88),
        },
        {
            "title": "The Matrix",
            "slug": "the-matrix",
            "description": "A hacker discovers the truth about his reality and joins a rebellion.",
            "director": "Lana Wachowski",
            "actor_1": "Keanu Reeves",
            "actor_2": "Laurence Fishburne",
            "actor_3": "Carrie-Anne Moss",
            "actor_4": "Hugo Weaving",
            "release_year": 1999,
            "poster": "the-matrix.png",
            "color": (12, 92, 72),
        },
        {
            "title": "Parasite",
            "slug": "parasite",
            "description": "A poor family schemes to become employed by a wealthy household.",
            "director": "Bong Joon-ho",
            "actor_1": "Song Kang-ho",
            "actor_2": "Lee Sun-kyun",
            "actor_3": "Cho Yeo-jeong",
            "actor_4": "Choi Woo-shik",
            "release_year": 2019,
            "poster": "parasite.png",
            "color": (120, 48, 48),
        },
        {
            "title": "Spirited Away",
            "slug": "spirited-away",
            "description": "A girl enters a magical world ruled by a witch and must find her way home.",
            "director": "Hayao Miyazaki",
            "actor_1": "Rumi Hiiragi",
            "actor_2": "Miyu Irino",
            "actor_3": "Mari Natsuki",
            "actor_4": "Bunta Sugawara",
            "release_year": 2001,
            "poster": "spirited-away.png",
            "color": (48, 88, 120),
        },
    ]

    for movie in sample_movies:
        poster_filename = _ensure_poster(movie["poster"], movie["color"])
        if slug_exists(movie["slug"]):
            continue
        insert_movie(
            movie["title"],
            movie["slug"],
            movie["description"],
            movie["director"],
            movie["actor_1"],
            movie["actor_2"],
            movie["actor_3"],
            movie["actor_4"],
            movie["release_year"],
            poster_filename,
        )

    print(f"Seeded {len(sample_movies)} example movies.")


if __name__ == "__main__":
    seed_movies()
