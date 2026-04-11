"""
app.py — The Publishing Company

This is the Flask application factory. In Phase 0 it has just one route
(/ping) that proves the Airtable connection works. In Phase 1 we'll add
Supabase Auth and the Author portal on top.

WHAT IS A "factory" PATTERN?
Instead of creating one global Flask app, we write a function (create_app)
that BUILDS a new Flask app each time it's called. This is cleaner because:
  - It's easier to test (each test can make its own app)
  - It's easier to configure (prod vs dev)
  - It plays nicer with gunicorn
You call it once in run.py and it hands you back a ready-to-use app.
"""

import os
from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
)
from dotenv import load_dotenv

# Load .env before anything else so environment variables are available
load_dotenv()

# Our reusable Airtable helper functions (copied verbatim from the
# concierge-core-automations project)
from airtable_helpers import get_record, get_records
from config import PROJECTS_TABLE, PROJ_NAME, PROJ_STATUS, PROJ_SERVICE

# Supabase Auth wrapper + decorators
from auth.supabase_client import (
    login_user,
    logout_user,
    forgot_password as supa_forgot,
    reset_password as supa_reset,
)
from auth.decorators import login_required

# Airtable user mapping (Supabase user -> Airtable record)
from services.user_mapping import get_portal_user

# Airtable queries (all data-isolation happens here)
from services.airtable_queries import (
    get_projects_for_author,
    get_project_for_author,
    get_milestones_for_project,
    get_invoices_for_project,
)


def create_app():
    """
    Factory function that builds a new Flask app.
    Call this once from run.py to get the app instance.
    """
    app = Flask(__name__)

    # Load config from environment variables
    flask_env = os.environ.get("FLASK_ENV", "development")
    app.config["ENV"] = flask_env

    # SECURITY: the secret key signs every session cookie. If it leaks (or
    # we silently fall back to a hardcoded value in production) anyone can
    # forge a logged-in session cookie for any user. So:
    #   - In production:  REQUIRE an explicit FLASK_SECRET_KEY env var.
    #                     Refuse to start if missing — loud failure > silent
    #                     security hole.
    #   - In development: fall back to "dev-key" so local setup stays easy.
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        if flask_env == "production":
            raise RuntimeError(
                "FLASK_SECRET_KEY is required when FLASK_ENV=production. "
                "Generate one with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\" "
                "and set it in your hosting provider's env vars."
            )
        secret_key = "dev-key-not-for-production"
    app.config["SECRET_KEY"] = secret_key

    # Register routes
    register_routes(app)

    return app


def register_routes(app):
    """
    Attach all routes to the app.
    In Phase 1 we'll move these into blueprints (auth, portals, admin).
    For now everything lives here.
    """

    @app.route("/")
    def index():
        """
        Landing page. If logged in, redirect to dashboard.
        Otherwise, show a simple welcome with a login link.
        """
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("index.html")

    @app.route("/ping")
    def ping():
        """
        Health check that ALSO tests the Airtable connection.

        This route proves the entire Phase 0 plumbing works:
          1. Flask is running
          2. .env is loading
          3. Airtable PAT is valid
          4. airtable_helpers.py works in the new project
          5. config.py field IDs are correct

        If this returns projects, Phase 0 is done.
        """
        # Fetch up to 5 projects from Airtable
        projects = get_records(PROJECTS_TABLE)

        if not projects:
            return jsonify({
                "status": "error",
                "message": "Could not fetch projects from Airtable. Check your PAT in .env.",
            }), 500

        # Build a small preview of the first few projects
        preview = []
        for p in projects[:5]:
            fields = p.get("fields", {})
            preview.append({
                "id": p.get("id"),
                "name": fields.get(PROJ_NAME, "(no name)"),
                "status": fields.get(PROJ_STATUS, "(no status)"),
                "service": fields.get(PROJ_SERVICE, "(no service)"),
            })

        return jsonify({
            "status": "ok",
            "airtable_connected": True,
            "total_projects": len(projects),
            "preview": preview,
            "message": "Phase 0 plumbing works. Airtable connection confirmed.",
        })

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """
        Login page. GET renders the form, POST processes it.
        On successful login, stores user info in the Flask session
        and redirects to the dashboard.
        """
        # Already logged in? Go to dashboard.
        if session.get("user_id"):
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            # Basic validation
            if not email or not password:
                flash("Email and password are required.", "error")
                return render_template("auth/login.html")

            # Hand off to Supabase
            result = login_user(email, password)

            if not result.get("success"):
                flash(result.get("error", "Login failed."), "error")
                return render_template("auth/login.html")

            # Look up the user in the Portal Users Airtable table.
            # This resolves their role and links them to their data.
            portal_user = get_portal_user(result["email"])

            if not portal_user:
                # User authenticated with Supabase but has no Portal Users record.
                # They shouldn't have access. Clear any partial state.
                flash(
                    "Your account isn't set up for portal access. "
                    "Please contact Julie.",
                    "error",
                )
                return render_template("auth/login.html")

            # Success — store everything we need in the session.
            # Sessions are signed cookies, safe for non-sensitive data.
            session["user_id"] = result["user_id"]
            session["email"] = result["email"]
            session["access_token"] = result["access_token"]
            session["refresh_token"] = result["refresh_token"]
            session["role"] = portal_user["role"]
            session["portal_user_id"] = portal_user["portal_user_id"]
            session["linked_author_id"] = portal_user["linked_author_id"]
            session["linked_partner_id"] = portal_user["linked_partner_id"]
            session["linked_internal_id"] = portal_user["linked_internal_id"]
            session.permanent = True  # 31-day default lifetime

            flash(f"Welcome back!", "success")
            return redirect(url_for("dashboard"))

        # GET — just show the form
        return render_template("auth/login.html")

    @app.route("/logout")
    def logout():
        """Log out the current user by clearing the session."""
        access_token = session.get("access_token")

        # Best-effort: tell Supabase to revoke the token
        if access_token:
            logout_user(access_token)

        # Clear our Flask session regardless
        session.clear()
        flash("You've been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/forgot-password", methods=["GET", "POST"])
    def forgot_password():
        """Trigger Supabase to send a password reset email."""
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()

            if not email:
                flash("Enter an email address.", "error")
                return render_template("auth/forgot.html")

            # Supabase sends the email and handles the reset link
            result = supa_forgot(
                email,
                redirect_to=url_for("reset_password", _external=True),
            )

            # Always show a success message even on failure
            # (don't leak whether an email exists in the system)
            flash(
                "If that email is registered, a reset link has been sent.",
                "info",
            )
            return redirect(url_for("login"))

        return render_template("auth/forgot.html")

    @app.route("/reset-password", methods=["GET", "POST"])
    def reset_password():
        """
        Landing page after user clicks the reset email link.

        GET: Renders reset.html. A small JS snippet in that template
             reads the access_token out of the URL fragment (#access_token=...)
             that Supabase added to the reset link, and puts it into a
             hidden form field. Fragments are browser-only — Flask never
             sees them — which is why we need JS to do this hand-off.

        POST: The form submits with three fields:
                - access_token (hidden, filled in by JS)
                - new_password
                - confirm_password
              We validate them, then call Supabase to update the password.
        """
        if request.method == "POST":
            access_token = request.form.get("access_token", "").strip()
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")

            # Missing token means either the email link was broken, or
            # the user navigated here directly without clicking the link.
            if not access_token:
                flash(
                    "Your reset link is missing or expired. "
                    "Please request a new one.",
                    "error",
                )
                return redirect(url_for("forgot_password"))

            # Basic validation (the JS also checks these, but never trust
            # the browser — always re-check on the server)
            if not new_password or not confirm_password:
                flash("Both password fields are required.", "error")
                return render_template("auth/reset.html")

            if new_password != confirm_password:
                flash("Passwords don't match. Please try again.", "error")
                return render_template("auth/reset.html")

            if len(new_password) < 8:
                flash("Password must be at least 8 characters.", "error")
                return render_template("auth/reset.html")

            # Hand off to Supabase — it verifies the token and updates
            # the user's password in one call.
            result = supa_reset(access_token, new_password)

            if not result.get("success"):
                flash(
                    result.get("error", "Could not update password. "
                                        "Your reset link may have expired."),
                    "error",
                )
                return redirect(url_for("forgot_password"))

            flash(
                "Password updated. You can now log in with your new password.",
                "success",
            )
            return redirect(url_for("login"))

        # GET — show the form
        return render_template("auth/reset.html")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """
        Dashboard — shows the logged-in user their actual info from Airtable.
        Protected by @login_required.
        """
        # Look up the user's Airtable record based on their role
        display_name = None
        linked_record_type = None

        if session.get("linked_author_id"):
            from airtable_helpers import get_record
            from config import AUTHORS_TABLE, AUTHOR_NAME

            author = get_record(AUTHORS_TABLE, session["linked_author_id"])
            if author:
                display_name = author.get("fields", {}).get(AUTHOR_NAME)
                linked_record_type = "Author"

        return render_template(
            "dashboard.html",
            email=session.get("email"),
            user_id=session.get("user_id"),
            role=session.get("role"),
            display_name=display_name,
            linked_record_type=linked_record_type,
            linked_author_id=session.get("linked_author_id"),
        )

    @app.route("/projects")
    @login_required
    def projects_list():
        """
        List all projects for the logged-in author.
        Uses the data-isolation chokepoint in airtable_queries.py.
        """
        author_id = session.get("linked_author_id")
        if not author_id:
            flash("No author record linked to your account.", "error")
            return redirect(url_for("dashboard"))

        projects = get_projects_for_author(author_id)
        return render_template("author/projects_list.html", projects=projects)

    @app.route("/projects/<project_id>")
    @login_required
    def project_detail(project_id):
        """
        Show a single project's details along with its author-visible
        milestones. Ownership is enforced at the query layer.
        """
        author_id = session.get("linked_author_id")
        project = get_project_for_author(author_id, project_id)

        if not project:
            flash("Project not found.", "error")
            return redirect(url_for("projects_list"))

        milestones = get_milestones_for_project(author_id, project_id)
        invoices = get_invoices_for_project(author_id, project_id)

        return render_template(
            "author/project_detail.html",
            project=project,
            milestones=milestones,
            invoices=invoices,
        )

    # NOTE: The /debug/whoami route was removed before the first production
    # deploy (April 11, 2026). It accepted an email + password in URL query
    # parameters, which would leak credentials into server logs and browser
    # history. It served its purpose during Phase 1 local development.
