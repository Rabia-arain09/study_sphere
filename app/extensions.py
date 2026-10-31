"""Database, migration, auth, and security extension instances for StudySphere."""

from sqlalchemy import MetaData
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

# Standardized constraint naming convention for seamless cross-database migrations (PostgreSQL/SQLite)
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata: MetaData = MetaData(naming_convention=NAMING_CONVENTION)

db: SQLAlchemy = SQLAlchemy(metadata=metadata)
migrate: Migrate = Migrate()
login_manager: LoginManager = LoginManager()
csrf: CSRFProtect = CSRFProtect()
