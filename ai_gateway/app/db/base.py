"""Общая декларативная база SQLAlchemy для таблиц Gateway."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Объединить ORM-модели в общие метаданные для SQLAlchemy и Alembic."""

    pass  # noqa: PIE790
