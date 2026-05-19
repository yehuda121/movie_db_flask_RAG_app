"""Flask movie database application."""

import os
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from database.db import (
    get_all_movies,
    get_movie_by_slug,
    get_popular_movies,
    get_reviews_for_movie,
    init_db,
    insert_movie,
    insert_review,
    slug_exists,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

STATIC_FOLDER = os.path.join(BASE_DIR, "static")
TEMPLATE_FOLDER = os.path.join(BASE_DIR, "templates")
POSTER_FOLDER = os.path.join(STATIC_FOLDER, "images", "posters")

# Explicit paths so static/templates work regardless of working directory (Docker-ready)
app = Flask(
    __name__,
    static_folder=STATIC_FOLDER,
    static_url_path="/static",
    template_folder=TEMPLATE_FOLDER,
)
app.secret_key = os.environ.get("SECRET_KEY", "movie-app-learning-secret-key")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

MAX_QUESTION_LENGTH = 150


def validate_ask_question(raw_question):
    """
    Clean and validate Ask AI questions.
    Returns (is_valid, error_message, cleaned_question).
    """
    cleaned = raw_question.strip()
    if not cleaned:
        return False, "Please enter a question.", cleaned
    if len(cleaned) > MAX_QUESTION_LENGTH:
        return (
            False,
            "Question is too long. Maximum length is 150 characters.",
            cleaned,
        )
    return True, None, cleaned


def rebuild_rag_index_safe():
    """Rebuild FAISS index and return (success, message)."""
    try:
        from rag.faiss_index import rebuild_rag_index

        count = rebuild_rag_index()
        return True, f"RAG index rebuilt successfully ({count} movies indexed)."
    except Exception as error:
        return False, f"RAG index rebuild failed: {error}"


def allowed_file(filename):
    """Return True if the uploaded file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view):
    """Decorator: redirect to admin login if user is not logged in."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin area.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def validate_review_form(form):
    """Validate review form fields. Returns (is_valid, error_message)."""
    reviewer_name = form.get("reviewer_name", "").strip()
    rating = form.get("rating", "").strip()
    review_text = form.get("review_text", "").strip()

    if not reviewer_name:
        return False, "Reviewer name is required."
    if not rating:
        return False, "Rating is required."
    try:
        rating_value = int(rating)
    except ValueError:
        return False, "Rating must be a number between 1 and 5."
    if rating_value < 1 or rating_value > 5:
        return False, "Rating must be between 1 and 5."
    if not review_text:
        return False, "Review text is required."

    return True, None


def validate_movie_form(form, require_poster=True):
    """Validate admin movie form fields. Returns (is_valid, error_message, cleaned_data)."""
    fields = {
        "title": form.get("title", "").strip(),
        "slug": form.get("slug", "").strip().lower(),
        "description": form.get("description", "").strip(),
        "director": form.get("director", "").strip(),
        "actor_1": form.get("actor_1", "").strip(),
        "actor_2": form.get("actor_2", "").strip(),
        "actor_3": form.get("actor_3", "").strip(),
        "actor_4": form.get("actor_4", "").strip(),
        "release_year": form.get("release_year", "").strip(),
    }

    required_labels = {
        "title": "Title",
        "slug": "Slug",
        "description": "Description",
        "director": "Director",
        "actor_1": "Actor 1",
        "actor_2": "Actor 2",
        "actor_3": "Actor 3",
        "actor_4": "Actor 4",
        "release_year": "Release year",
    }

    for key, label in required_labels.items():
        if not fields[key]:
            return False, f"{label} is required.", None

    try:
        fields["release_year"] = int(fields["release_year"])
    except ValueError:
        return False, "Release year must be a valid number.", None

    if require_poster and "poster" not in request.files:
        return False, "Poster image is required.", None

    return True, None, fields


@app.route("/")
def home():
    """Homepage: popular movies grid with optional title search."""
    # Read search text from URL query string, e.g. /?q=bat
    search_query = request.args.get("q", "").strip()
    movies = get_popular_movies(search_query)
    return render_template(
        "home.html",
        movies=movies,
        search_query=search_query,
    )


@app.route("/ask", methods=["GET", "POST"])
def ask_ai():
    """Ask AI page: RAG question answering over movie database."""
    from rag.retrieval import MIN_CONTEXT_SCORE, ask_question

    question = ""
    answer = None
    sources = []
    error_message = None

    submitted_question = ""
    show_retrieval_section = False
    min_context_score = MIN_CONTEXT_SCORE

    if request.method == "POST":
        raw_question = request.form.get("question", "")
        is_valid, validation_error, question = validate_ask_question(raw_question)

        if not is_valid:
            error_message = validation_error
            # Keep trimmed text in the textarea when validation fails
        else:
            submitted_question = question
            result = ask_question(question)
            if result["error"] and not result["success"]:
                error_message = result["error"]
                sources = result.get("sources", [])
                show_retrieval_section = result.get("show_retrieval_section", False)
            else:
                answer = result["answer"]
                sources = result["sources"]
                show_retrieval_section = result.get("show_retrieval_section", False)
                if result.get("clear_input"):
                    question = ""

    return render_template(
        "ask_ai.html",
        question=question,
        submitted_question=submitted_question,
        answer=answer,
        sources=sources,
        error_message=error_message,
        show_retrieval_section=show_retrieval_section,
        min_context_score=min_context_score,
        max_question_length=MAX_QUESTION_LENGTH,
    )


@app.route("/movie/<slug>", methods=["GET", "POST"])
def movie_details(slug):
    """Movie details page with reviews and review form."""
    movie = get_movie_by_slug(slug)
    if movie is None:
        abort(404)

    if request.method == "POST":
        is_valid, error_message = validate_review_form(request.form)
        if not is_valid:
            flash(error_message, "error")
        else:
            insert_review(
                movie["id"],
                request.form.get("reviewer_name", "").strip(),
                int(request.form.get("rating")),
                request.form.get("review_text", "").strip(),
            )
            flash("Thank you! Your review was submitted.", "success")
            return redirect(url_for("movie_details", slug=slug))

    reviews = get_reviews_for_movie(movie["id"])
    return render_template(
        "movie_details.html",
        movie=movie,
        reviews=reviews,
    )


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Simple admin login using Flask session."""
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Welcome back, admin!", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    """Log out admin and clear session."""
    session.pop("admin_logged_in", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    """Admin dashboard with link to add movies."""
    movies = get_all_movies()
    return render_template("admin_dashboard.html", movies=movies)


@app.route("/admin/rag/rebuild", methods=["POST"])
@login_required
def admin_rebuild_rag():
    """Manually rebuild the FAISS RAG index from SQLite."""
    success, message = rebuild_rag_index_safe()
    flash(message, "success" if success else "error")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/movies/add", methods=["GET", "POST"])
@login_required
def add_movie():
    """Add a new movie (admin only)."""
    if request.method == "POST":
        is_valid, error_message, fields = validate_movie_form(request.form)
        if not is_valid:
            flash(error_message, "error")
            return render_template("add_movie.html", form=request.form)

        if slug_exists(fields["slug"]):
            flash("This slug is already used by another movie.", "error")
            return render_template("add_movie.html", form=request.form)

        poster_file = request.files.get("poster")
        if not poster_file or poster_file.filename == "":
            flash("Poster image is required.", "error")
            return render_template("add_movie.html", form=request.form)

        if not allowed_file(poster_file.filename):
            flash("Allowed poster types: png, jpg, jpeg, webp.", "error")
            return render_template("add_movie.html", form=request.form)

        safe_name = secure_filename(poster_file.filename)
        # Prefix with slug to reduce name collisions
        poster_filename = f"{fields['slug']}-{safe_name}"
        save_path = os.path.join(POSTER_FOLDER, poster_filename)
        poster_file.save(save_path)

        insert_movie(
            fields["title"],
            fields["slug"],
            fields["description"],
            fields["director"],
            fields["actor_1"],
            fields["actor_2"],
            fields["actor_3"],
            fields["actor_4"],
            fields["release_year"],
            poster_filename,
        )
        flash(f"Movie '{fields['title']}' was added successfully.", "success")

        rag_ok, rag_message = rebuild_rag_index_safe()
        if rag_ok:
            flash(rag_message, "success")
        else:
            flash(rag_message, "warning")

        return redirect(url_for("admin_dashboard"))

    return render_template("add_movie.html", form={})


@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 page for missing routes or movie slugs."""
    return render_template("404.html"), 404


def setup_app():
    """Create folders, database tables, posters, and optional seed data."""
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "data", "faiss"), exist_ok=True)
    os.makedirs(os.path.join(STATIC_FOLDER, "css"), exist_ok=True)
    os.makedirs(POSTER_FOLDER, exist_ok=True)
    init_db()

    from database.seed import ensure_posters_from_database, seed_movies

    ensure_posters_from_database()
    seed_movies()

    # Build RAG index on first run if missing (may take a minute on first download)
    try:
        from rag.retrieval import ensure_rag_index

        ensure_rag_index()
    except Exception as error:
        print(f"RAG index setup skipped: {error}")


if __name__ == "__main__":
    setup_app()
    # Use FLASK_DEBUG=1 in docker-compose for development; 0 for safer runs
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
