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
import uuid
from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load .env before anything else so environment variables are available
load_dotenv()

# Our reusable Airtable helper functions (copied verbatim from the
# concierge-core-automations project)
from airtable_helpers import get_record, get_records
from config import (
    PROJECTS_TABLE, PROJ_NAME, PROJ_STATUS, PROJ_SERVICE,
    TASKS_TABLE, TASK_NAME, TASK_STATUS, TASK_DUE_DATE,
    TASK_ASSIGNED_PARTNER,
)

# Supabase Auth wrapper + decorators
from auth.supabase_client import (
    login_user,
    logout_user,
    forgot_password as supa_forgot,
    reset_password as supa_reset,
)
from auth.decorators import login_required, role_required

# Airtable user mapping (Supabase user -> Airtable record)
from services.user_mapping import get_portal_user

# Airtable queries (all data-isolation happens here)
from services.airtable_queries import (
    get_projects_for_author,
    get_project_for_author,
    get_milestones_for_project,
    get_invoices_for_project,
    get_partner_name,
    get_partner_type,
    get_tasks_for_task_partner,
    get_projects_for_channel_partner,
    get_project_for_channel_partner,
    get_files_for_task,
    create_file_record,
    get_all_projects,
    get_all_tasks,
    get_all_invoices,
    get_all_partners,
    get_task_detail,
    update_task,
    get_milestones_for_channel_project,
    get_invoices_for_channel_project,
    get_project_detail_admin,
    get_partner_detail_admin,
    get_available_services,
    get_all_authors,
    get_lead_projects,
    inject_milestones,
    create_deposit_invoice,
    create_balance_invoice,
    create_invoice,
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

    # File uploads — temporary storage so Airtable can download them.
    # Files are saved here briefly, then Airtable copies them to its own
    # storage. The temp files can be cleaned up periodically.
    upload_dir = os.path.join(app.root_path, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB max

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
            session["display_name"] = portal_user.get("display_name", "")
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

        Supabase can redirect here two ways depending on auth config:
          1. PKCE flow (newer): /reset-password?code=xxx
             → We exchange the code for an access_token server-side
          2. Implicit flow (older): /reset-password#access_token=xxx
             → JS reads the fragment and puts it in a hidden field

        We handle both so it works regardless of Supabase version.
        """
        # --- PKCE flow: exchange ?code= for an access token on GET ---
        pkce_code = request.args.get("code")
        pkce_token = None
        if pkce_code:
            from auth.supabase_client import exchange_code_for_session
            session_result = exchange_code_for_session(pkce_code)
            if session_result.get("success"):
                pkce_token = session_result["access_token"]

        if request.method == "POST":
            # Try PKCE token from hidden field first, then legacy hash token
            access_token = (
                request.form.get("access_token", "").strip()
            )
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

        # GET — show the form (pass PKCE token if we got one)
        return render_template("auth/reset.html", pkce_token=pkce_token or "")

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """
        Dashboard — role-aware landing page after login.
        Authors see their author dashboard. Partners see their partner view.
        """
        role = session.get("role", "")
        display_name = None

        # Admin → Command Center
        if role == "Admin":
            return redirect(url_for("command_center"))

        # Author dashboard
        if session.get("linked_author_id"):
            from config import AUTHORS_TABLE, AUTHOR_NAME
            author = get_record(AUTHORS_TABLE, session["linked_author_id"])
            if author:
                display_name = author.get("fields", {}).get(AUTHOR_NAME)

            return render_template(
                "dashboard.html",
                email=session.get("email"),
                user_id=session.get("user_id"),
                role=role,
                display_name=display_name,
                linked_record_type="Author",
                linked_author_id=session.get("linked_author_id"),
            )

        # Partner dashboard (Task Partner or Channel Partner)
        if session.get("linked_partner_id"):
            partner_id = session["linked_partner_id"]
            display_name = get_partner_name(partner_id)
            partner_type = get_partner_type(partner_id)

            # Task Partners see their assigned tasks grouped by project
            if role == "Task Partner":
                project_tasks = get_tasks_for_task_partner(partner_id)
                return render_template(
                    "partner/dashboard.html",
                    email=session.get("email"),
                    role=role,
                    display_name=display_name,
                    partner_type=partner_type,
                    project_tasks=project_tasks,
                )

            # Channel Partners see their linked projects
            if role == "Channel Partner":
                projects = get_projects_for_channel_partner(partner_id)
                return render_template(
                    "partner/dashboard.html",
                    email=session.get("email"),
                    role=role,
                    display_name=display_name,
                    partner_type=partner_type,
                    projects=projects,
                )

        # Fallback — no linked record
        return render_template(
            "dashboard.html",
            email=session.get("email"),
            user_id=session.get("user_id"),
            role=role,
            display_name=None,
            linked_record_type=None,
            linked_author_id=None,
        )

    @app.route("/projects")
    @login_required
    @role_required("Author")
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
    @role_required("Author")
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

    # ============================================================
    # PARTNER ROUTES
    # ============================================================

    @app.route("/partner/projects/<project_id>")
    @login_required
    @role_required("Task Partner", "Channel Partner")
    def partner_project_detail(project_id):
        """
        Project detail for partners. What they see depends on their role:
        - Task Partner: their assigned tasks + basic project info (no billing)
        - Channel Partner: full project view with milestones + billing
        """
        role = session.get("role", "")
        partner_id = session.get("linked_partner_id")

        if not partner_id:
            flash("No partner record linked to your account.", "error")
            return redirect(url_for("dashboard"))

        if role == "Task Partner":
            # Task Partners don't have a traditional "project view" —
            # their tasks are shown on the dashboard. But if they click
            # through, show them their tasks for this specific project.
            project_tasks = get_tasks_for_task_partner(partner_id)
            # Find the specific project from the grouped results
            project_data = None
            for proj in project_tasks:
                if proj["project_id"] == project_id:
                    project_data = proj
                    break

            if not project_data:
                flash("Project not found or you have no tasks on it.", "error")
                return redirect(url_for("dashboard"))

            return render_template(
                "partner/project_detail_task.html",
                project=project_data,
            )

        if role == "Channel Partner":
            project = get_project_for_channel_partner(partner_id, project_id)
            if not project:
                flash("Project not found.", "error")
                return redirect(url_for("dashboard"))

            milestones = get_milestones_for_channel_project(partner_id, project_id)
            invoices = get_invoices_for_channel_project(partner_id, project_id)

            return render_template(
                "partner/project_detail_channel.html",
                project=project,
                milestones=milestones,
                invoices=invoices,
            )

        flash("Unknown partner type.", "error")
        return redirect(url_for("dashboard"))

    # ============================================================
    # COMMAND CENTER ROUTES (Admin only)
    # ============================================================

    @app.route("/command-center")
    @app.route("/command-center/<tab>")
    @login_required
    @role_required("Admin")
    def command_center(tab="tasks"):
        """
        Command Center — Julie's ops dashboard.
        Tabbed layout: Tasks | Projects | Partners
        """
        # Greeting: prefer Display Name from Airtable, fall back to email prefix
        first_name = (
            session.get("display_name")
            or (session.get("email", "").split("@")[0].capitalize() if session.get("email") else "")
            or "there"
        )

        # Priority tasks: overdue, due today, or needing action — shown on every tab
        all_tasks = get_all_tasks()
        priority_tasks = [
            t for t in all_tasks
            if t["is_overdue"]
            or (t.get("next_step") and t["next_step"].get("action"))
            or t["is_due_soon"]
        ]

        if tab == "tasks":
            return render_template(
                "command_center/tasks.html",
                tab=tab,
                tasks=all_tasks,
                first_name=first_name,
                priority_tasks=priority_tasks,
            )
        elif tab == "projects":
            projects = get_all_projects()
            return render_template(
                "command_center/projects.html",
                tab=tab,
                projects=projects,
                first_name=first_name,
                priority_tasks=priority_tasks,
            )
        elif tab == "financials":
            invoices = get_all_invoices()
            # Calculate summary totals
            total_revenue = sum(i["amount_paid"] or 0 for i in invoices)
            total_outstanding = sum(i["outstanding"] or 0 for i in invoices)
            total_overdue = sum(
                i["outstanding"] or 0 for i in invoices if i["is_overdue"]
            )
            return render_template(
                "command_center/financials.html",
                tab=tab,
                invoices=invoices,
                total_revenue=total_revenue,
                total_outstanding=total_outstanding,
                total_overdue=total_overdue,
                first_name=first_name,
                priority_tasks=priority_tasks,
            )
        elif tab == "partners":
            partners = get_all_partners()
            return render_template(
                "command_center/partners.html",
                tab=tab,
                partners=partners,
                first_name=first_name,
                priority_tasks=priority_tasks,
            )

        # Unknown tab — fall back to tasks
        return redirect(url_for("command_center", tab="tasks"))

    @app.route("/command-center/task/<task_id>", methods=["GET", "POST"])
    @login_required
    @role_required("Admin")
    def command_center_task_detail(task_id):
        """
        Task detail page — view and edit a single task.
        """
        if request.method == "POST":
            # Build the update dict from the form
            updates = {}

            new_status = request.form.get("status")
            if new_status:
                updates[TASK_STATUS] = new_status

            new_due_date = request.form.get("due_date")
            if new_due_date:
                updates[TASK_DUE_DATE] = new_due_date

            new_instructions = request.form.get("instructions")
            if new_instructions is not None:
                updates["fldB74YCkAJ055mis"] = new_instructions

            new_notes = request.form.get("notes")
            if new_notes is not None:
                updates["fldGlObVe6dyOSZci"] = new_notes

            # Assigned Partner — linked record field (needs to be a list)
            new_partner = request.form.get("assigned_partner")
            if new_partner:
                updates[TASK_ASSIGNED_PARTNER] = [new_partner]
            elif new_partner == "":
                # User chose "Unassigned" — clear the link
                updates[TASK_ASSIGNED_PARTNER] = []

            if updates:
                from config import TASK_STATUS as TS, TASK_DUE_DATE as TD
                result = update_task(task_id, updates)
                if result:
                    flash("Task updated.", "success")
                else:
                    flash("Update failed.", "error")

            return redirect(url_for("command_center_task_detail", task_id=task_id))

        task = get_task_detail(task_id)
        if not task:
            flash("Task not found.", "error")
            return redirect(url_for("command_center", tab="tasks"))

        # Fetch partners for the assignment dropdown
        partners = get_all_partners()

        return render_template(
            "command_center/task_detail.html",
            task=task,
            partners=partners,
        )

    @app.route("/command-center/project/<project_id>", methods=["GET", "POST"])
    @login_required
    @role_required("Admin")
    def command_center_project_detail(project_id):
        """
        Project detail page — everything about one project in one place.
        GET: view project details.
        POST: update project fields.
        """
        if request.method == "POST":
            from airtable_helpers import update_record
            from config import (
                PROJECTS_TABLE, PROJ_STATUS, PROJ_SERVICE,
                PROJ_START_DATE, PROJ_DEPOSIT_PAID,
                PROJ_CONTRACT_STATUS, PROJ_CONTRACT_SENT_DATE,
                PROJ_CONTRACT_SIGNED_DATE,
            )

            updates = {}

            # Collect form fields — only update what was submitted
            status = request.form.get("status")
            if status:
                updates[PROJ_STATUS] = status

            service = request.form.get("service")
            if service is not None:
                updates[PROJ_SERVICE] = service

            start_date = request.form.get("start_date")
            if start_date is not None:
                updates[PROJ_START_DATE] = start_date if start_date else None

            # Checkbox — present in form = checked, absent = unchecked
            deposit_paid = "deposit_paid" in request.form
            updates[PROJ_DEPOSIT_PAID] = deposit_paid

            contract_status = request.form.get("contract_status")
            if contract_status is not None:
                updates[PROJ_CONTRACT_STATUS] = contract_status if contract_status else None

            contract_sent = request.form.get("contract_sent_date")
            if contract_sent is not None:
                updates[PROJ_CONTRACT_SENT_DATE] = contract_sent if contract_sent else None

            contract_signed = request.form.get("contract_signed_date")
            if contract_signed is not None:
                updates[PROJ_CONTRACT_SIGNED_DATE] = contract_signed if contract_signed else None

            if updates:
                result = update_record(PROJECTS_TABLE, project_id, updates)
                if result:
                    flash("Project updated.", "success")
                else:
                    flash("Update failed.", "error")

            return redirect(url_for("command_center_project_detail", project_id=project_id))

        project = get_project_detail_admin(project_id)
        if not project:
            flash("Project not found.", "error")
            return redirect(url_for("command_center", tab="projects"))

        return render_template(
            "command_center/project_detail.html",
            project=project,
        )

    @app.route("/command-center/partner/<partner_id>")
    @login_required
    @role_required("Admin")
    def command_center_partner_detail(partner_id):
        """
        Partner detail page — bio, projects, tasks, and payment history.
        """
        partner = get_partner_detail_admin(partner_id)
        if not partner:
            flash("Partner not found.", "error")
            return redirect(url_for("command_center", tab="partners"))

        return render_template(
            "command_center/partner_detail.html",
            partner=partner,
        )

    # ============================================================
    # ADMIN PREVIEW — View as Author / Partner
    # ============================================================

    @app.route("/command-center/preview-as/<role_type>/<record_id>")
    @login_required
    @role_required("Admin")
    def admin_preview_start(role_type, record_id):
        """
        Start previewing the portal as a specific author or partner.
        Stores the preview state in the session so all pages render
        in that role's view. The real Admin role is preserved so we
        can restore it.
        """
        # Save the real admin session so we can restore it
        session["admin_preview"] = True
        session["real_role"] = "Admin"
        session["real_linked_author_id"] = session.get("linked_author_id")
        session["real_linked_partner_id"] = session.get("linked_partner_id")

        if role_type == "author":
            session["role"] = "Author"
            session["linked_author_id"] = record_id
            session["linked_partner_id"] = None
        elif role_type == "task-partner":
            session["role"] = "Task Partner"
            session["linked_partner_id"] = record_id
            session["linked_author_id"] = None
        elif role_type == "channel-partner":
            session["role"] = "Channel Partner"
            session["linked_partner_id"] = record_id
            session["linked_author_id"] = None

        flash(f"Previewing as {session['role']}. Click 'Back to Command Center' to exit.", "info")
        return redirect(url_for("dashboard"))

    @app.route("/command-center/preview-exit")
    @login_required
    def admin_preview_exit():
        """Stop previewing and restore the Admin session."""
        if session.get("admin_preview"):
            session["role"] = session.pop("real_role", "Admin")
            session["linked_author_id"] = session.pop("real_linked_author_id", None)
            session["linked_partner_id"] = session.pop("real_linked_partner_id", None)
            session.pop("admin_preview", None)
            flash("Back to Command Center.", "info")
        return redirect(url_for("command_center"))

    # ============================================================
    # PROJECT STARTUP
    # ============================================================

    @app.route("/command-center/project-startup", methods=["GET", "POST"])
    @login_required
    @role_required("Admin")
    def project_startup():
        """
        Project startup wizard.
        GET: shows the form (create new or activate existing Lead)
        POST: creates/updates the project, injects milestones, redirects to detail
        """
        if request.method == "POST":
            from airtable_helpers import create_record, update_record
            from config import (
                PROJECTS_TABLE, PROJ_NAME, PROJ_AUTHOR, PROJ_SERVICE,
                PROJ_STATUS, PROJ_START_DATE, PROJ_DEPOSIT_PAID,
            )
            from datetime import date

            mode = request.form.get("mode")  # "new" or "activate"

            if mode == "new":
                # Create a brand new project
                author_id = request.form.get("author_id", "")
                service = request.form.get("service", "")
                project_name = request.form.get("project_name", "")
                start_date = request.form.get("start_date", date.today().isoformat())

                if not project_name:
                    flash("Project name is required.", "error")
                    return redirect(url_for("project_startup"))

                fields = {
                    PROJ_NAME: project_name,
                    PROJ_SERVICE: service,
                    PROJ_STATUS: "Active",
                    PROJ_START_DATE: start_date,
                }
                if author_id:
                    fields[PROJ_AUTHOR] = [author_id]

                result = create_record(PROJECTS_TABLE, fields)
                if not result:
                    flash("Could not create project.", "error")
                    return redirect(url_for("project_startup"))

                project_id = result.get("id")

                # Parse start date so milestones can chain due dates sequentially
                try:
                    parsed_start = date.fromisoformat(start_date)
                except (ValueError, TypeError):
                    parsed_start = date.today()

                # Inject milestones from the Milestone Library
                if service:
                    count = inject_milestones(project_id, service, start_date=parsed_start)
                    flash(f"Project created with {count} tasks from the {service} template.", "success")
                else:
                    flash("Project created (no service selected — no tasks injected).", "success")

                # Auto-create deposit invoice
                dep_invoice = create_deposit_invoice(project_id)
                if dep_invoice:
                    flash("Deposit invoice created.", "success")

                return redirect(url_for("command_center_project_detail", project_id=project_id))

            elif mode == "activate":
                # Activate an existing Lead project
                project_id = request.form.get("project_id", "")
                service = request.form.get("activate_service", "")
                start_date = request.form.get("activate_start_date", date.today().isoformat())

                if not project_id:
                    flash("Select a project to activate.", "error")
                    return redirect(url_for("project_startup"))

                updates = {
                    PROJ_STATUS: "Active",
                    PROJ_START_DATE: start_date,
                }
                if service:
                    updates[PROJ_SERVICE] = service

                update_record(PROJECTS_TABLE, project_id, updates)

                # Parse start date so milestones can chain due dates sequentially
                try:
                    parsed_start = date.fromisoformat(start_date)
                except (ValueError, TypeError):
                    parsed_start = date.today()

                # Inject milestones
                if service:
                    count = inject_milestones(project_id, service, start_date=parsed_start)
                    flash(f"Project activated with {count} tasks from the {service} template.", "success")
                else:
                    flash("Project activated (no service selected — no tasks injected).", "success")

                # Auto-create deposit invoice
                dep_invoice = create_deposit_invoice(project_id)
                if dep_invoice:
                    flash("Deposit invoice created.", "success")

                return redirect(url_for("command_center_project_detail", project_id=project_id))

        # GET — show the startup form
        services = get_available_services()
        authors = get_all_authors()
        leads = get_lead_projects()

        from datetime import date
        return render_template(
            "command_center/project_startup.html",
            services=services,
            authors=authors,
            leads=leads,
            today=date.today().isoformat(),
        )

    # ---- API endpoints for inline actions ----

    @app.route("/api/task/<task_id>/status", methods=["POST"])
    @login_required
    @role_required("Admin")
    def api_update_task_status(task_id):
        """
        AJAX endpoint — update a task's status without page reload.
        Expects JSON: {"status": "Complete"}
        """
        data = request.get_json()
        if not data or "status" not in data:
            return jsonify({"success": False, "error": "Missing status"}), 400

        result = update_task(task_id, {TASK_STATUS: data["status"]})
        if result:
            response = {"success": True, "status": data["status"]}

            # Check if this task completion triggers a balance invoice
            if data["status"] == "Complete":
                task_record = get_record(TASKS_TABLE, task_id)
                if task_record:
                    task_fields = task_record.get("fields", {})
                    task_name = task_fields.get(TASK_NAME, "")
                    task_seq = task_fields.get("fldtyvvJzWoGu68ie", 0)  # TASK_SEQUENCE

                    # Get the project to check if this is the balance trigger
                    proj_links = task_fields.get("fldj1YwlwJbfK956K", [])
                    if proj_links:
                        proj_id = proj_links[0]
                        proj = get_record(PROJECTS_TABLE, proj_id)
                        if proj:
                            proj_fields = proj.get("fields", {})
                            trigger_milestone = proj_fields.get("fldE8fei45sX5ld9u", "")
                            trigger_seq = proj_fields.get("fldkavRlqhIjdGyF8", 0)

                            # Match by name or sequence number
                            if (trigger_milestone and trigger_milestone == task_name) or \
                               (trigger_seq and trigger_seq == task_seq):
                                inv = create_balance_invoice(proj_id)
                                if inv:
                                    response["balance_invoice_created"] = True

            return jsonify(response)
        return jsonify({"success": False, "error": "Update failed"}), 500

    # ---- Task management: Add / Delete ----

    @app.route("/api/task/<task_id>/delete", methods=["POST"])
    @login_required
    @role_required("Admin")
    def api_delete_task(task_id):
        """Delete a task from a project."""
        from airtable_helpers import delete_record
        from config import TASKS_TABLE

        result = delete_record(TASKS_TABLE, task_id)
        if result:
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Delete failed"}), 500

    @app.route("/api/project/<project_id>/add-task", methods=["POST"])
    @login_required
    @role_required("Admin")
    def api_add_task(project_id):
        """
        Add a new task to a project.
        Expects JSON: {"name": "Task Name", "module": "Editorial", "due_date": "2026-05-01"}
        """
        from airtable_helpers import create_record
        from config import (
            TASKS_TABLE, TASK_NAME, TASK_PROJECT,
            TASK_MODULE, TASK_STATUS, TASK_DUE_DATE, TASK_SEQUENCE,
        )

        data = request.get_json()
        if not data or not data.get("name"):
            return jsonify({"success": False, "error": "Task name is required"}), 400

        # Build the new task record
        fields = {
            TASK_NAME: data["name"],
            TASK_PROJECT: [project_id],  # Link to the project
            TASK_STATUS: "Not Started",
        }

        if data.get("module"):
            fields[TASK_MODULE] = data["module"]
        if data.get("due_date"):
            fields[TASK_DUE_DATE] = data["due_date"]
        if data.get("sequence"):
            fields[TASK_SEQUENCE] = int(data["sequence"])

        result = create_record(TASKS_TABLE, fields)
        if result:
            return jsonify({
                "success": True,
                "task_id": result.get("id"),
            })
        return jsonify({"success": False, "error": "Create failed"}), 500

    # ---- Invoices: Manual creation ----

    @app.route("/api/project/<project_id>/create-invoice", methods=["POST"])
    @login_required
    @role_required("Admin")
    def api_create_invoice(project_id):
        """
        Manually create an invoice for a project (add-on services, custom charges).
        Expects JSON: {"amount": 2000, "type": "Add-On", "description": "AI Edition"}
        """
        data = request.get_json()
        if not data or not data.get("amount"):
            return jsonify({"success": False, "error": "Amount is required"}), 400

        try:
            amount = float(data["amount"])
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid amount"}), 400

        inv_type = data.get("type", "Add-On")
        description = data.get("description", "")

        # Get author ID from the project
        project = get_record(PROJECTS_TABLE, project_id)
        if not project:
            return jsonify({"success": False, "error": "Project not found"}), 404

        proj_fields = project.get("fields", {})
        project_name = proj_fields.get(PROJ_NAME, "")
        author_links = proj_fields.get("fldNGhEZJuOBGv1lW", [])
        author_id = author_links[0] if author_links else ""

        # Use description as the type label if provided
        label = description if description else inv_type

        result = create_invoice(project_id, author_id, label, amount, project_name)
        if result:
            return jsonify({"success": True, "invoice_id": result.get("id")})
        return jsonify({"success": False, "error": "Could not create invoice"}), 500

    # ---- Disbursements: Payment requests ----

    @app.route("/api/disbursement", methods=["POST"])
    @login_required
    def api_create_disbursement():
        """
        Create a payment request (disbursement).
        Can be called by Admin (from project detail) or Partner (from task view).
        Expects JSON with: amount, type, notes, project_id, task_id (optional), partner_id
        """
        from airtable_helpers import create_record
        from config import (
            DISBURSEMENTS_TABLE, DISB_NAME, DISB_PARTNER,
            DISB_TYPE, DISB_PROJECT, DISB_TASK,
            DISB_AMOUNT_REQUESTED, DISB_REQUESTED_DATE,
            DISB_PAYMENT_STATUS, DISB_NOTES,
        )
        from datetime import date

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400

        amount = data.get("amount")
        if not amount:
            return jsonify({"success": False, "error": "Amount is required"}), 400

        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Invalid amount"}), 400

        partner_id = data.get("partner_id")
        project_id = data.get("project_id")
        task_id = data.get("task_id")
        disb_type = data.get("type", "Partner Fee")
        notes = data.get("notes", "")

        # Build a descriptive name
        disb_name = f"Payment Request — ${amount:,.0f}"

        fields = {
            DISB_NAME: disb_name,
            DISB_AMOUNT_REQUESTED: amount,
            DISB_TYPE: disb_type,
            DISB_REQUESTED_DATE: date.today().isoformat(),
            DISB_PAYMENT_STATUS: "Pending",
        }

        if partner_id:
            fields[DISB_PARTNER] = [partner_id]
        if project_id:
            fields[DISB_PROJECT] = [project_id]
        if task_id:
            fields[DISB_TASK] = [task_id]
        if notes:
            fields[DISB_NOTES] = notes

        result = create_record(DISBURSEMENTS_TABLE, fields)
        if result:
            return jsonify({
                "success": True,
                "disbursement_id": result.get("id"),
            })
        return jsonify({"success": False, "error": "Could not create disbursement"}), 500

    # ---- Typeflow: Send SOW / MSA ----

    @app.route("/api/send-sow/<project_id>", methods=["POST"])
    @login_required
    @role_required("Admin")
    def api_send_sow(project_id):
        """
        Trigger Typeflow to generate and send a Statement of Work
        for a project. Updates the contract status in Airtable.
        """
        from services.typeflow import send_sow
        from airtable_helpers import update_record
        from config import (
            PROJECTS_TABLE, PROJ_CONTRACT_STATUS, PROJ_CONTRACT_SENT_DATE,
        )
        from datetime import date

        result = send_sow(project_id)

        if result["success"]:
            # Update the project's contract status in Airtable
            update_record(PROJECTS_TABLE, project_id, {
                PROJ_CONTRACT_STATUS: "Sent",
                PROJ_CONTRACT_SENT_DATE: date.today().isoformat(),
            })
            return jsonify({
                "success": True,
                "message": "SOW sent for signature.",
                "pdf_url": result.get("pdf_url", ""),
            })

        return jsonify({
            "success": False,
            "error": result.get("error", "Unknown error"),
        }), 500

    @app.route("/api/send-msa/<record_id>", methods=["POST"])
    @login_required
    @role_required("Admin")
    def api_send_msa(record_id):
        """
        Trigger Typeflow to generate and send a Master Service Agreement.
        The recipient_type query param tells us whether it's an author or partner.
        """
        from services.typeflow import send_msa

        # "author" or "partner" — defaults to "author"
        recipient_type = request.args.get("type", "author")

        result = send_msa(record_id, recipient_type=recipient_type)

        if result["success"]:
            return jsonify({
                "success": True,
                "message": "MSA sent for signature.",
                "pdf_url": result.get("pdf_url", ""),
            })

        return jsonify({
            "success": False,
            "error": result.get("error", "Unknown error"),
        }), 500

    # ============================================================
    # FILE UPLOAD / DOWNLOAD ROUTES
    # ============================================================

    @app.route("/uploads/<filename>")
    def serve_upload(filename):
        """
        Serve a temporarily uploaded file so Airtable can download it.
        This is how the handoff works:
          1. User uploads a file through the portal
          2. Flask saves it to the uploads/ folder
          3. We create an Airtable record pointing to this URL
          4. Airtable downloads the file and stores its own copy
          5. The temp file can be cleaned up later
        """
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/task/<task_id>/upload", methods=["GET", "POST"])
    @login_required
    def upload_file(task_id):
        """
        Upload a file to a task. Any role can upload — the direction
        field tracks who sent what:
          - Author/PM uploading → "To Partner" (source file)
          - Task Partner uploading → "From Partner" (deliverable)
          - Author uploading after review → "Author Review" (corrections)
        """
        role = session.get("role", "")

        if request.method == "POST":
            # Check that a file was included
            if "file" not in request.files:
                flash("No file selected.", "error")
                return redirect(request.url)

            file = request.files["file"]
            if file.filename == "":
                flash("No file selected.", "error")
                return redirect(request.url)

            # Get form data
            file_type = request.form.get("file_type", "Other")
            direction = request.form.get("direction", "")
            notes = request.form.get("notes", "")
            project_id = request.form.get("project_id", "")

            # Figure out who's uploading
            uploaded_by = session.get("email", "Unknown")

            # Save the file with a unique name to avoid collisions
            original_name = secure_filename(file.filename)
            unique_name = f"{uuid.uuid4().hex}_{original_name}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
            file.save(save_path)

            # Build the public URL so Airtable can download the file.
            # In production (Render), this will be the real domain.
            # In local dev, Airtable can't reach localhost — the record
            # will be created but the attachment won't download.
            file_url = url_for("serve_upload", filename=unique_name, _external=True)

            # Create the Project Files record in Airtable.
            # We pass the stored filename so the download link works
            # even on localhost (where Airtable can't fetch the file).
            result = create_file_record(
                task_id=task_id,
                project_id=project_id,
                file_name=original_name,
                file_url=file_url,
                file_type=file_type,
                direction=direction,
                uploaded_by=uploaded_by,
                notes=notes,
                stored_filename=unique_name,
            )

            if result:
                flash(f"File '{original_name}' uploaded successfully.", "success")
            else:
                flash("Upload failed — could not save to Airtable.", "error")

            # Redirect back to where they came from
            if role == "Task Partner":
                return redirect(url_for("dashboard"))
            elif role == "Channel Partner":
                return redirect(url_for("partner_project_detail", project_id=project_id))
            else:
                return redirect(url_for("dashboard"))

        # GET — show the upload form
        # We need the task info to show context
        task = get_record(TASKS_TABLE, task_id)
        if not task:
            flash("Task not found.", "error")
            return redirect(url_for("dashboard"))

        task_name = task.get("fields", {}).get(TASK_NAME, "(unnamed task)")

        # Get existing files for this task
        files = get_files_for_task(task_id)

        # Get the project ID from the task
        project_links = task.get("fields", {}).get("fldj1YwlwJbfK956K", [])
        project_id = project_links[0] if project_links else ""

        return render_template(
            "upload.html",
            task_id=task_id,
            task_name=task_name,
            project_id=project_id,
            files=files,
            role=role,
        )

    # NOTE: The /debug/whoami route was removed before the first production
    # deploy (April 11, 2026). It accepted an email + password in URL query
    # parameters, which would leak credentials into server logs and browser
    # history. It served its purpose during Phase 1 local development.
