from collections.abc import Generator
from contextlib import contextmanager
from functools import cache
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from mietmanager.models import Base

DEFAULT_DB_PATH = Path.home() / ".mietmanager" / "mietmanager.db"


@cache
def get_engine(db_path: Path = DEFAULT_DB_PATH) -> Engine:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine: Engine | None = None) -> Engine:
    engine = engine or get_engine()
    Base.metadata.create_all(engine)
    return engine


@cache
def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=engine or get_engine())


@contextmanager
def session_scope() -> Generator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
