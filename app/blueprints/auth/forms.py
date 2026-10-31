"""Form definitions for user authentication and student registration."""

from __future__ import annotations
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, NumberRange, ValidationError
try:
    from wtforms.fields.choices import SelectChoice
    SEMESTER_CHOICES = [SelectChoice(value=i, label=f"Semester {i}") for i in range(1, 9)]
except ImportError:  # pragma: no cover
    SEMESTER_CHOICES = [(i, f"Semester {i}") for i in range(1, 9)]
from app.models.user import User


class SignupForm(FlaskForm):
    """Registration form for new students joining StudySphere."""

    name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Please provide your full name."),
            Length(min=2, max=120, message="Name must be between 2 and 120 characters."),
        ],
    )
    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Please provide your email address."),
            Email(check_deliverability=False, message="Please enter a valid email address."),
            Length(max=255, message="Email must not exceed 255 characters."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please choose a secure password."),
            Length(min=6, max=128, message="Password must be at least 6 characters long."),
        ],
    )
    semester = SelectField(
        "Current Academic Semester",
        choices=SEMESTER_CHOICES,
        coerce=int,
        default=1,
        validators=[
            DataRequired(message="Please select your current semester."),
            NumberRange(min=1, max=8, message="Semester must be between 1 and 8."),
        ],
    )
    submit = SubmitField("Create Account")

    def validate_email(self, field: StringField) -> None:
        """Ensure email uniqueness across the platform.

        Args:
            field: Form field containing user email.

        Raises:
            ValidationError: If another user is registered with the same email.
        """
        normalized_email = field.data.strip().lower() if field.data else ""
        existing = User.query.filter(User.email.ilike(normalized_email)).first()
        if existing:
            raise ValidationError("An account with this email address already exists. Please sign in.")


class LoginForm(FlaskForm):
    """Login form for returning students and instructors."""

    email = StringField(
        "Email Address",
        validators=[
            DataRequired(message="Please enter your email address."),
            Email(check_deliverability=False, message="Please enter a valid email address."),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please enter your password."),
        ],
    )
    remember = BooleanField("Remember me on this device")
    submit = SubmitField("Sign In")
