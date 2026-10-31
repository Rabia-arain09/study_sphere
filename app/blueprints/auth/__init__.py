"""Authentication blueprint for user registration, login, session management, and logout."""

from __future__ import annotations
from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User
from app.blueprints.auth.forms import SignupForm, LoginForm

auth_bp: Blueprint = Blueprint("auth", __name__)


def is_safe_url(target: str | None) -> bool:
    """Validate that redirect target is an internal relative URL.

    Guards against open redirect vulnerabilities by rejecting external schemes,
    hostnames, and protocol-relative prefixes.

    Args:
        target: Target URL to evaluate.

    Returns:
        bool: True if safe for local redirect, False otherwise.
    """
    if not target or not isinstance(target, str):
        return False
    clean = target.strip()
    if clean.startswith(("//", "http://", "https://", "javascript:", "data:")):
        return False
    parts = urlsplit(clean)
    return parts.scheme == "" and parts.netloc == "" and parts.path.startswith("/")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Register a new student account."""
    if current_user.is_authenticated:
        return redirect(url_for("topics.semester_picker"))

    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            semester=form.semester.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f"Welcome to StudySphere, {user.name}! Your account has been created.", "success")

        next_page = request.args.get("next")
        if next_page and is_safe_url(next_page):
            return redirect(next_page)
        return redirect(url_for("topics.semester_picker"))

    return render_template("auth/signup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate existing students and instructors."""
    if current_user.is_authenticated:
        return redirect(url_for("topics.semester_picker"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(User.email.ilike(email)).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")

            next_page = request.args.get("next")
            if next_page and is_safe_url(next_page):
                return redirect(next_page)
            return redirect(url_for("topics.semester_picker"))

        flash("Invalid email or password. Please verify your credentials and try again.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    """Sign out the current user and terminate the active session."""
    logout_user()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth.login"))
