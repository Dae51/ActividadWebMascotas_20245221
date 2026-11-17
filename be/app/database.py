from collections.abc import Generator, Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def transaction(db: Session) -> Iterator[Session]:
    """Commit once per unit of work; roll back everything on failure.

    Repositories only flush, so a service can compose several writes (adoption
    plus pet transfer plus notifications) into a single atomic transaction.
    """
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
