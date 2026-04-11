"""
decorators.py — Route decorators for access control.

WHAT IS A DECORATOR?
A decorator is a function that wraps another function to add behavior.
In Flask, we use decorators to run code BEFORE a route runs — like
checking if the user is logged in.

HOW TO USE:
    @app.route("/dashboard")
    @login_required
    def dashboard():
        return "..."

The @login_required decorator runs first. If the user isn't logged in,
it redirects to /login. If they ARE logged in, it lets the original
function run normally.

This is the pattern Flask-Login uses, but we're writing our own simple
version because we're using Supabase for auth and don't need the full
Flask-Login machinery.
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(view_func):
    """
    Protect a route so only logged-in users can access it.

    Checks for user_id in the Flask session. If missing, flashes a
    message and redirects to /login. Otherwise, runs the route normally.
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    """
    Protect a route so only users with specific roles can access it.

    Usage:
        @app.route("/admin")
        @login_required
        @role_required("admin")
        def admin_page():
            ...

    The role is stored in the session when the user logs in (after we
    look them up in the Portal Users Airtable table). This decorator
    checks that the session role matches one of the allowed roles.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            user_role = session.get("role")
            if user_role not in allowed_roles:
                flash("You don't have permission to view that page.", "error")
                return redirect(url_for("dashboard"))
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
