"""Database manager for SQLite / PostgreSQL persistence."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import (
    Base,
    Course,
    CourseGroupTime,
    GovernanceConfig,
    GovernanceResult,
    GovernanceRun,
    Organization,
    Session as SessionModel,
    StudentTask,
    User,
)

logger = logging.getLogger(__name__)

TABLE_MODEL_MAP = {
    "users": User,
    "organizations": Organization,
    "courses": Course,
    "sessions": SessionModel,
    "student_tasks": StudentTask,
    "course_group_times": CourseGroupTime,
    "governance_results": GovernanceResult,
    "governance_runs": GovernanceRun,
    "governance_configs": GovernanceConfig,
}


class DatabaseManager:
    """Manage database connections, table creation, and CRUD operations."""

    def __init__(self, database_url: str = "sqlite:///lms.db"):
        self.database_url = database_url
        if database_url.startswith("sqlite:///"):
            self.engine = create_engine(
                database_url,
                future=True,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(database_url, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all defined tables."""
        Base.metadata.create_all(self.engine)
        logger.info("Tables created")

    def migrate_columns(self) -> None:
        """Add missing columns to existing tables (SQLite-safe)."""
        inspector = inspect(self.engine)
        dialect = self.engine.dialect.name

        for table_name, model in TABLE_MODEL_MAP.items():
            if not inspector.has_table(table_name):
                continue

            existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
            for column in model.__table__.columns:
                if column.name in existing_columns:
                    continue

                if dialect == "sqlite":
                    # SQLite requires default for NOT NULL columns
                    default_clause = ""
                    if not column.nullable and column.default is None:
                        if isinstance(column.type, (String, Text)):
                            default_clause = " DEFAULT ''"
                        elif isinstance(column.type, (Integer,)):
                            default_clause = " DEFAULT 0"
                        elif isinstance(column.type, (Boolean,)):
                            default_clause = " DEFAULT 0"
                        elif isinstance(column.type, (DateTime,)):
                            default_clause = " DEFAULT CURRENT_TIMESTAMP"

                    col_type = column.type.compile(dialect=self.engine.dialect)
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{default_clause}"
                    try:
                        with self.engine.begin() as conn:
                            conn.execute(text(sql))
                        logger.info("Added column %s.%s", table_name, column.name)
                    except Exception as exc:
                        logger.warning("Failed to add column %s.%s: %s", table_name, column.name, exc)
                else:
                    # PostgreSQL and others — use Alembic for real migrations
                    logger.warning("Column migration not implemented for dialect: %s", dialect)

    def migrate_constraints(self) -> None:
        """Rebuild SQLite tables when unique constraints need updating."""
        inspector = inspect(self.engine)
        if self.engine.dialect.name != "sqlite":
            return

        # Check users table: umu_id was standalone unique, now composite (synced_by, umu_id)
        if inspector.has_table("users"):
            constraints = inspector.get_unique_constraints("users")
            for c in constraints:
                if "umu_id" in c.get("column_names", []) and len(c.get("column_names", [])) == 1:
                    self._rebuild_table("users", TABLE_MODEL_MAP["users"])
                    logger.info("Rebuilt users table for composite unique constraint")
                    break

        # Check courses table: course_id was standalone unique, now composite (synced_by, course_id)
        if inspector.has_table("courses"):
            constraints = inspector.get_unique_constraints("courses")
            for c in constraints:
                if "course_id" in c.get("column_names", []) and len(c.get("column_names", [])) == 1:
                    self._rebuild_table("courses", TABLE_MODEL_MAP["courses"])
                    logger.info("Rebuilt courses table for composite unique constraint")
                    break

    def _rebuild_table(self, table_name: str, model) -> None:
        """Rebuild a SQLite table to apply schema changes (e.g. unique constraints)."""
        from sqlalchemy import MetaData, Table

        inspector = inspect(self.engine)
        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}

        temp_name = f"{table_name}_new"
        metadata = MetaData()
        new_table = Table(temp_name, metadata)

        for col in model.__table__.columns:
            new_table.append_column(col.copy())

        for constraint in model.__table__.constraints:
            if isinstance(constraint, UniqueConstraint):
                new_table.append_constraint(
                    UniqueConstraint(
                        *[c.name for c in constraint.columns],
                        name=constraint.name,
                    )
                )

        with self.engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            new_table.create(self.engine)

            common_cols = existing_cols & {c.name for c in model.__table__.columns}
            col_str = ", ".join(common_cols)
            conn.execute(text(f"INSERT INTO {temp_name} ({col_str}) SELECT {col_str} FROM {table_name}"))
            conn.execute(text(f"DROP TABLE {table_name}"))
            conn.execute(text(f"ALTER TABLE {temp_name} RENAME TO {table_name}"))
            conn.execute(text("PRAGMA foreign_keys=ON"))

        logger.info("Rebuilt table %s", table_name)

    def create_table_from_schema(self, table_name: str, schema: dict) -> None:
        """Dynamically create a table from a JSON schema descriptor."""
        from sqlalchemy import Column, MetaData, String, Table

        metadata = MetaData()
        columns = [Column("id", String(64), primary_key=True)]
        for field_name, field_info in schema.get("properties", {}).items():
            if field_name == "id":
                continue
            col_type = String(512)
            columns.append(Column(field_name, col_type))
        columns.append(Column("raw_data", String))

        table = Table(table_name, metadata, *columns)
        metadata.create_all(self.engine)
        logger.info("Created table %s", table_name)

    def save(self, table_name: str, records: list[dict]) -> int:
        """Bulk insert or update records into a table."""
        model = TABLE_MODEL_MAP.get(table_name)
        if not model:
            logger.warning("No ORM model for table %s; skipping", table_name)
            return 0

        count = 0
        with self.SessionLocal() as session:
            with session.begin():
                for record in records:
                    obj = self._record_to_model(model, record)
                    session.merge(obj)
                    count += 1
        logger.info("Saved %d records to %s", count, table_name)
        return count

    def _record_to_model(self, model: Any, record: dict) -> Any:
        """Map a flat record dict to an ORM model instance."""
        kwargs: dict[str, Any] = {"raw_data": record}
        for col in model.__table__.columns:
            if col.name in record:
                kwargs[col.name] = record[col.name]
        return model(**kwargs)

    def query(self, table_name: str, **filters: Any) -> list[dict]:
        """Query records from a table with optional filters."""
        model = TABLE_MODEL_MAP.get(table_name)
        if not model:
            return []

        with self.SessionLocal() as session:
            q = session.query(model)
            for key, value in filters.items():
                if hasattr(model, key):
                    q = q.filter(getattr(model, key) == value)
            results = q.all()
            return [self._model_to_dict(r) for r in results]

    def _model_to_dict(self, obj: Any) -> dict:
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    def get_stats(self, table_name: str) -> dict[str, Any]:
        """Return row count and column info for a table."""
        inspector = inspect(self.engine)
        if not inspector.has_table(table_name):
            return {"exists": False, "count": 0}

        with self.SessionLocal() as session:
            model = TABLE_MODEL_MAP.get(table_name)
            if model:
                count = session.query(model).count()
            else:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()

        return {
            "exists": True,
            "count": count,
            "columns": [c["name"] for c in inspector.get_columns(table_name)],
        }

    def migrate_from_api(
        self,
        endpoint_callable: Any,
        table_name: str,
        batch_size: int = 100,
        **call_kwargs: Any,
    ) -> int:
        """Fetch all data from an API endpoint and persist to database."""
        total = 0
        records = endpoint_callable(**call_kwargs)
        if not isinstance(records, list):
            logger.warning("Expected list from endpoint, got %s", type(records))
            return 0

        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            total += self.save(table_name, batch)

        return total
