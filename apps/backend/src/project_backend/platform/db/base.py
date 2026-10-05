from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Alembic autogenerate reads Base.metadata. ORM models live in their module's
    infrastructure/persistence/models.py and must be imported in migrations/env.py."""
