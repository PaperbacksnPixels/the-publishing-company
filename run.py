"""
run.py — Entry point for The Publishing Company

LOCAL DEVELOPMENT:
    venv\\Scripts\\python run.py
    (then open http://localhost:5000 in your browser)

PRODUCTION (on Render or similar):
    gunicorn run:app
    (Render runs this automatically via the Procfile)

Both paths call create_app() from app.py, so there's only one place
the Flask app is actually built.
"""

from app import create_app

# Build the app instance ONCE at module load time.
# Gunicorn looks for a variable named "app" in this file.
app = create_app()


if __name__ == "__main__":
    # This block only runs when you launch the file directly
    # (e.g. `python run.py`). Gunicorn ignores it.
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
